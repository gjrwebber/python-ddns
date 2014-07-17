import urllib2

class Network(object):

    def get_wan_ip(self):
        page = urllib2.urlopen("http://checkip.dyndns.org/").read()
        marker = "IP Address: "
        start = page.find(marker) + len(marker)
        end = page.find("<", start)
        return page[start:end]
