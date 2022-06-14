import os
from xml.etree import ElementTree
import dict2xml
import json
import requests
import gzip
import time
from datetime import datetime, timezone, timedelta, tzinfo
from backports.zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row
import boto3
from chalice import Chalice, NotFoundError

app = Chalice(app_name='pace-bus-tracker')
_TABLE = None

ssm_client = boto3.client('ssm')
environment = os.environ['ENVIRONMENT']
raw_config = ssm_client.get_parameters_by_path(Path=f'/pace-bus-tracker/{environment}', Recursive=True, WithDecryption=True)
config = { entry['Name'].replace(f'/pace-bus-tracker/{environment}/', '', 1) : entry['Value'] for entry in raw_config['Parameters'] }

@app.route('/available/{year}/{month}/{day}', cors=True)
def available(year, month, day):
    reqZone = None
    if app.current_request.query_params != None:
        reqZone = app.current_request.query_params.get('timezone')
    if reqZone == None:
        reqZone = "UTC"
    start = datetime(int(year), int(month), int(day), tzinfo=ZoneInfo(reqZone)).astimezone(timezone.utc)
    end = start + timedelta(1)

    response_start = get_app_table().get_item(
        Key={
            'key': 'archive_index',
            'range_key': start.isoformat().split('T')[0].replace('-','/')
        }
    )
    response_end = get_app_table().get_item(
        Key={
            'key': 'archive_index',
            'range_key': end.isoformat().split('T')[0].replace('-','/')
        }
    )

    start_entries = response_start.get('Item', { 'entries': dict() })['entries']
    end_entries = response_end.get('Item', { 'entries': dict() })['entries']
    entries = {**start_entries, **end_entries}
    filtered_entries = dict(filter(lambda elem: datetime.fromtimestamp(int(elem[0]), tz=timezone.utc) >= start and datetime.fromtimestamp(int(elem[0]), tz=timezone.utc) <= end,
        entries.items()))

    if len(filtered_entries) == 0:
        raise NotFoundError(f'No archives available for {year}-{month}-{day}')
    return filtered_entries

@app.route('/runs/{property_tag}', cors=True)
def available(property_tag):
    start = None
    if app.current_request.query_params != None:
        start = app.current_request.query_params.get('start')
    if start == None:
        start = datetime.now()
    else:
        start = datetime.utcfromtimestamp(int(start))
    
    ret = []

    with psycopg.connect(db_connection_string(), row_factory=dict_row) as conn:
        cur = conn.execute("SELECT routes.abbr, max(tmstmp) at time zone 'america/chicago' at time zone 'utc' as end, min(tmstmp) at time zone 'america/chicago' at time zone 'utc' as start FROM vehicles JOIN routes on routes.id = vehicles.route_id WHERE property_tag = %(property_tag)s and tmstmp <= %(start)s and tmstmp >= %(start)s - INTERVAL '90 days' GROUP BY routes.abbr, date_trunc('day', tmstmp) ORDER BY max(tmstmp) desc",
            {'property_tag': property_tag, 'start': start})
        for record in cur:
            ret.append({
                'route_abbr': record['abbr'],
                'start': datetime.timestamp(record['start']),
                'end': datetime.timestamp(record['end']),
            })

    return {
        'runs': ret,
        'next': int(datetime.timestamp(start - timedelta(days=90)))
    }

@app.schedule('cron(*/10 * * * ? *)')
def refresh(evt):
  do_refresh()

def do_refresh():
    to_upload = gzip.compress(("<?xml version=\"1.0\"?>\n<?xml-stylesheet type=\"text/xsl\" href=\"/bus-rte.xsl\"?><root>" + dict2xml.dict2xml(paceData()) + "</root>").encode('utf-8'))
    ts = int(time.time())
    time_path = datetime.fromtimestamp(ts).strftime('%Y/%m/%d')
    dest_path = f'archive/{time_path}/buses-in-service-{ts}.xml'
    now = datetime.now()
    now_plus_10 = now + timedelta(minutes = 10)
    client = boto3.client('s3')
    client.put_object(Body=to_upload, Bucket=config['s3.bucket_name'], Key=dest_path, ContentEncoding='gzip', ContentType='text/xml')
    client.put_object(Body=to_upload, Bucket=config['s3.bucket_name'], Key='buses-in-service.xml', ContentEncoding='gzip', ContentType='text/xml', Expires=now_plus_10)

    response = get_app_table().get_item(
        Key={
            'key': 'archive_index',
            'range_key': time_path
        }
    )

    entries = dict()
    if 'Item' in response.keys():
        entries = response['Item']['entries']
    entries[str(ts)] = dest_path
    get_app_table().put_item(
        Item={
            'key': 'archive_index',
            'range_key': time_path,
            'entries': entries
        }
    )

@app.on_s3_event(bucket=config['s3.bucket_name'], events=['s3:ObjectCreated:*'], prefix="archive/")
def process_new_archive(event):
    import_archive_to_postgres(event.bucket, event.key)

def import_archive_to_postgres(bucket, key):
    client = boto3.client('s3')
    obj = client.get_object(Bucket=bucket, Key=key)
    root = ElementTree.fromstring(gzip.decompress(obj['Body'].read()))
    tmstmp = root.find('./timestamp').text
    with psycopg.connect(db_connection_string(), row_factory=dict_row) as conn:
        for route in root.findall('./routes'):
            conn.execute('INSERT INTO routes (id, abbr, name) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET abbr = EXCLUDED.abbr, name = EXCLUDED.name',
                [
                    route.find('./id').text,
                    route.find('./abbr').text if route.find('./abbr') != None else None,
                    route.find('./name').text if route.find('./name') != None else None,
                ])
        for vehicle in root.findall('./buses'):
            conn.execute('INSERT INTO vehicles (property_tag, tmstmp, lat_long, heading, route_id) VALUES (%s, %s, POINT(%s, %s)::geometry, %s, %s) ON CONFLICT (property_tag, tmstmp) DO NOTHING',
                [
                    vehicle.find('./propertyTag').text,
                    tmstmp,
                    vehicle.find('./lat').text if vehicle.find('./lat') != None else None,
                    vehicle.find('./lon').text if vehicle.find('./lon') != None else None,
                    vehicle.find('./heading').text if vehicle.find('./heading') != None else None,
                    vehicle.find('./routeID').text if vehicle.find('./routeID') != None else None
                ])
        conn.commit()


def paceData():
  routes = requests.post('https://tmweb.pacebus.com/TMWebWatch/MultiRoute.aspx/getRouteInfo', headers={'User-Agent': 'bus-tracker-archiver', 'Content-Type': 'application/json'}, data='').json()['d']
  buses = []
  for route in routes:
    route_id = route['id']
    route_buses = requests.post('https://tmweb.pacebus.com/TMWebWatch/GoogleMap.aspx/getVehicles', headers={'user-agent': 'bus-tracker-archiver'}, json={'routeID': route_id}).json()['d']
    if route_buses:
      buses.extend(route_buses)
    
  return { 'timestamp': datetime.now(tz=ZoneInfo('America/Chicago')).strftime("%Y%m%d %H:%M:%S"), 'routes': routes, 'buses': buses }

def get_app_table():
    global _TABLE
    if _TABLE is None:
        _TABLE = boto3.resource('dynamodb').Table(config['archive_table_name'])
        
    return _TABLE

def db_connection_string():
    return f'host={config["db.host"]} user={config["db.username"]} password={config["db.password"]} dbname={config["db.database"]}'

def main():
  import_archive_to_postgres(config['s3.bucket_name'], "buses-in-service.xml")

if __name__ == '__main__':
    main()
