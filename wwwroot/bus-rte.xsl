<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="html"/>
  <xsl:variable name="root" select="/"/>
  <xsl:template match="/root">
    <html>
      <head>
        <meta charset="utf-8"/>
        <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <script src="/js/jquery.min.js"/>
        <script src="/js/jquery.filtertable.js"/>
        <script src="/js/jquery.timeago.js"/>
        <script src="/js/iframeResizer.contentWindow.min.js"/>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous" />
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.min.js" integrity="sha384-cVKIPhGWiC2Al4u+LWgxfKTRIcfu0JTxR+EQDz/bgldoEyl4H0zUF0QKbrJ0EcQF" crossorigin="anonymous"></script>
        <script>
                  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
                  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
                  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
                  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

                  ga('create', 'UA-73091403-1', 'auto');
                  ga('send', 'pageview');

                </script>
        <style>
                .filter-table .quick { margin-left: 0.5em; font-size: 0.8em; text-decoration: none; }
                .fitler-table .quick:hover { text-decoration: underline; }
                td.alt { background-color: #ffc; background-color: rgba(255, 255, 0, 0.2); }
                </style>
        <title>Pace Buses in Service</title>
      </head>
      <body>
        <div id="main" class="container">
          <h4>Pace Buses in Service</h4>
          <div class="accordion" id="accordion" role="tablist" aria-multiselectable="true">
            <xsl:apply-templates select="document('series.xml')/series/*">
              <xsl:sort select="@no" data-type="number"/>
            </xsl:apply-templates>
          </div>
        </div>
        <footer class="footer container">
							Last updated: <span id="updatetime"><xsl:value-of select="timestamp"/></span>
			</footer>
        <script>
				$(function() {
				    $('table').filterTable(); //if this code appears after your tables; otherwise, include it in your document.ready() code.
				    var regex = /(\d{4})(\d{2})(\d{2}) (\d{2}):(\d{2}):(\d{2})/;
				    var dateArray = regex.exec($("#updatetime").html());
				    var dateObject = new Date(
				        (+dateArray[1]),
				        (+dateArray[2])-1, // Careful, month starts at 0!
				        (+dateArray[3]),
				        (+dateArray[4]),
				        (+dateArray[5]),
				        (+dateArray[6])
				    );
				    $("#updatetime").html($.timeago(dateObject));
				});
				</script>
      </body>
    </html>
  </xsl:template>
  <xsl:template match="series">
    <xsl:variable name="series" select="range/@start"/>
    <xsl:variable name="series-name" select="@name"/>
    <div class="accordion-item">
      <h4 class="accordion-header" id="heading{$series}">
        <button class="accordion-button collapsed" data-bs-toggle="collapse" data-bs-target="#collapse{$series}" href="#collapse{$series}" aria-expanded="true" aria-controls="collapse{$series}">
         <xsl:value-of select="$series-name"/>
         (<xsl:value-of select="$series"/>)
        </button>
      </h4>
      <div id="collapse{$series}" data-bs-parent="#accordion" class="accordion-collapse collapse" role="tabpanel" aria-labelledby="heading{$series}">
        <div class="accordion-body table-responsive">
          <table class="table table-hover table-condensed">
            <thead>
              <tr bgcolor="#9acd32">
                <th>Bus #</th>
                <th>Route #</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="range">
                <xsl:variable name="range-start" select="@start"/>
                <xsl:variable name="range-end" select="@end"/>
                <xsl:apply-templates select="$root/*/buses[$range-start &lt;= propertyTag and propertyTag &lt;= $range-end ]">
                  <xsl:sort select="propertyTag" data-type="number"/>
                </xsl:apply-templates>
              </xsl:for-each>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </xsl:template>
  <xsl:template match="error">
    <tr>
      <td>
        <xsl:value-of select="propertyTag"/>
      </td>
      <td>
                —
	    	</td>
    </tr>
  </xsl:template>
  <xsl:template match="buses">
    <tr>
      <td>
        <xsl:value-of select="propertyTag"/>
      </td>
      <td>
        <xsl:value-of select="routeAbbr"/>
        <xsl:variable name="routeId" select="routeID"/>
        <xsl:text>: </xsl:text>
        <xsl:value-of select="/root/routes[id=$routeId]/name"/>
      </td>
    </tr>
  </xsl:template>
</xsl:stylesheet>
