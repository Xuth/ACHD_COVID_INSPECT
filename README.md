# ACHD_COVID_INSPECT
script to scrape the Allegheny County Health Department COVID restaurant reports and convert them into a spreadsheet.

This generates a simple CSV file with ratings and comments from each of the restaurant reports accessible on https://eapps.alleghenycounty.us/cFips/cDashBoard.aspx.  (eventually there will be more than 1 page of data and this tool will have to learn to deal with that)

It downloads the XML file for each of the reports (and caches it locally so that subsequent runs don't repeatedly download the same reports) and then creates a summary spreadsheet with a line for each report.

This requires gdbm (which should be installed with python but often isn't)  and xmltotext.

