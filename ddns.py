"""

General help:

to run from the commandline:

  python -m pyfooware.ddns godaddy

run with -h for a list of options


GoDaddy help:

to update GoDaddy DNS, first create the file $HOME/.godaddyrc with the
following three properties:

    username=myuser
    password=mypass
    domains=domain1.com,domain2.org

the following updates GoDaddy and logs output to syslog (good for cron)

  python -m pyfooware.ddns godaddy -L

"""

import network
import os.path
import sys
import syslog

class DDNSError(Exception):
    
    def __init__(self, message, error=None):
        self.message = message
        self.error = error

    def __repr__(self):
        return self.message

    def __str__(self):
        return self.message

class DNSProvider(object):

    def __init__(self, logging, syslog_ident):
        self.logging_on = logging
        self.syslogging_on = bool(syslog_ident)
        if syslog_ident:
            syslog.openlog(syslog_ident, facility=syslog.LOG_USER)

    def update(self):
        pass

    def log(self, message):
        if self.logging_on:
            print message
        if self.syslogging_on:
            syslog.syslog(syslog.LOG_ALERT, message)

    def error(self, message):
        if self.logging_on:
            print >> sys.stderr, message
        if self.syslogging_on:
            syslog.syslog(syslog.LOG_ALERT, message)


class GoDaddy(DNSProvider):

    def __init__(self, config_path=None, logging=False, syslog_ident=None):
        DNSProvider.__init__(self, logging, syslog_ident)
        self.config_path = config_path
        if not self.config_path:
            self.config_path = os.path.expanduser("~/.godaddyrc")
        self._init_from_config()

    def _init_from_config(self):
        props = {}
        lnbr = 0
        try:
            for line in open(self.config_path):
                lnbr += 1
                line = line.strip()
                i = line.find("#")
                if i >= 0:
                    line = line[:i]
                if not line:
                    continue
                name, value = line.split("=")
                props[name] = value
        except ValueError as e:
            msg = "invalid config value [line %s]: %s" % (lnbr, line)
            self.error(msg)
            raise DDNSError(msg)
        except Exception as e:
            msg =  "error reading %s (%s)" % (self.config_path, `e`)
            self.error(msg)
            raise DDNSError(msg, e)
        self.username = props.get("username", None)
        if not self.username:
            msg = "no godaddy username configured"
            self.error(msg)
            raise DDNSError(msg)
        self.password = props.get("password", None)
        if not self.password:
            msg = "no godaddy password configured"
            self.error(msg)
            raise DDNSError(msg)
        self.domains = filter(lambda d: d != '',
                props.get("domains", "").split(","))
        if not self.domains:
            msg = "no godaddy domains not configured"
            self.error(msg)
            raise DDNSError(msg)

    def update(self):
        wan_ip = network.Network().get_wan_ip()
        self.log("router wan ip is " + wan_ip)
        godaddy = pygodaddy.GoDaddyClient()
        if not godaddy.login(self.username, self.password):
            msg = "godaddy login failure for " + self.username
            self.error(msg)
            raise DDNSError(msg)
        for domain in self.domains:
            for rec in godaddy.find_dns_records(domain):
                if not rec.hostname == "@":
                    continue
                if rec.value == wan_ip:
                    self.log("%s: already set to %s" % (domain, wan_ip))
                    continue
                self.log("%s: updating from %s to %s" %
                        (domain, rec.value, wan_ip))
                if not godaddy.update_dns_record(domain, wan_ip):
                    msg = "failed to update %s dns record" % domain
                    self.error(msg)
                    raise DDNSError(msg)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("provider",
            metavar="name",
            help="dns provider name")
    parser.add_argument("-l", "--log",
            dest="logging",
            action="store_true",
            help="log to stdout")
    parser.add_argument("-L", "--syslog",
            metavar="ident",
            dest="syslog_ident",
            nargs="?",
            help="log to syslog (ident defaults to ddns_<provider>)")
    args = parser.parse_args(sys.argv[1:])
    try:
        name = sys.argv[1]
        provider = None
        if name == "godaddy":
            try:
                import pygodaddy
            except ImportError as e:
                msg = "pygodaddy module not found: " + \
                        "https://pygodaddy.readthedocs.org/"
                print >> sys.stderr, msg
                raise DDNSError(msg)
            ident = args.syslog_ident
            if not ident:
                ident = "ddns_" + args.provider
            provider = GoDaddy(logging=args.logging, syslog_ident=ident)
        if not provider:
            msg = "unknown dns provider: " + name
            print >> sys.stderr, msg
            raise DDNSError(msg)
        provider.update()
    except DDNSError as e:
        print "fatal error:", e
        sys.exit(1)
