import requests
from six.moves import urllib

from cloud_info_provider import exceptions
from cloud_info_provider import providers
from cloud_info_provider import utils


class MesosProvider(providers.BaseProvider):
    service_type = "compute"
    goc_service_type = None

    def __init__(self, opts):
        super(MesosProvider, self).__init__(opts)

        self.framework_url = None
        self.framework_type = None
        self.api_endpoints = []

        if not any([opts.mesos_endpoint,
                    opts.marathon_endpoint]):
            msg = ('You must provide a Mesos, Marathon or Chronos API '
                   'endpoint via --mesos-endpoint, --marathon-endpoint or '
                   '--chronos-endpoint respectively (alternatively using '
                   'the environment variables MESOS_ENDPOINT, '
                   'MARATHON_ENDPOINT or CHRONOS_ENDPOINT)')
            raise exceptions.MesosProviderException(msg)
        if len(filter(None,
                      [opts.mesos_endpoint,
                       opts.marathon_endpoint])) > 1:
            msg = ('Please provide only one API endpoint')
            raise exceptions.MesosProviderException(msg)
        if opts.mesos_endpoint:
            self.framework_url = opts.mesos_endpoint
            self.framework_type = 'mesos'
            self.api_endpoints = ['/metrics/snapshot', 'state']
        elif opts.marathon_endpoint:
            self.framework_url = opts.marathon_endpoint
            self.framework_type = 'marathon'
            self.api_endpoints = ['v2/info', 'v2/leader']
        self.goc_service_type = 'eu.indigo-datacloud.%s' % self.framework_type

        self.static = providers.static.StaticProvider(opts)

        self.headers = {}
        if opts.oidc_token:
            self.headers['Authorization'] = 'Bearer %s' % opts.oidc_token

    def get_site_info(self):
        d = {}
        for endp in self.api_endpoints:
            api_url = urllib.parse.urljoin(self.framework_url, endp)
            api_url = '/'.join([self.framework_url, endp])
            r = requests.get(api_url, headers=self.headers)
            if r.status_code == requests.codes.ok:
                d.update(r.json())
        return d

    def get_compute_shares(self, **kwargs):
        shares = self.static.get_compute_shares(prefix=True)
        return shares

    def get_compute_endpoints(self, **kwargs):
        ret = {
            'endpoints': {
                self.framework_url: {}},
        }

        defaults = self.static.get_compute_endpoint_defaults(prefix=True)
        ret.update(defaults)
        return ret

    @staticmethod
    def populate_parser(parser):
        parser.add_argument(
            '--mesos-endpoint',
            metavar='<api-url>',
            default=utils.env('MESOS_ENDPOINT'),
            help=('Specify Mesos API endpoint. '
                  'Defaults to env[MESOS_ENDPOINT]'))
        parser.add_argument(
            '--marathon-endpoint',
            metavar='<api-url>',
            default=utils.env('MARATHON_ENDPOINT'),
            help=('Specify Marathon API endpoint. '
                  'Defaults to env[MARATHON_ENDPOINT]'))
        parser.add_argument(
            '--oidc-auth-bearer-token',
            metavar='<bearer-token>',
            default=utils.env('IAM_ACCESS_TOKEN'),
            dest='oidc_token',
            help=('Specify OIDC bearer token to use when '
                  'authenticating with the API. Defaults '
                  'to env[IAM_ACCESS_TOKEN]'))
