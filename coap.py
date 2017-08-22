#the coap server implementation
import socket
try:
    import ujson as json
except ImportError:
    import json
try:
    import ustruct as struct
except ImportError:
    import struct

from micropython import const

#coap methods
COAP_METHOD_GET = const(1)
COAP_METHOD_POST = const(2)
COAP_METHOD_PUT = const(3)
COAP_METHOD_DELETE = const(4)
#COAP message types
COAP_TYPE_CONFIRMABLE = const(0)
COAP_TYPE_NON_CONFIRMABLE = const(1)
COAP_TYPE_ACKNOWLEDGEMENT = const(2)
COAP_TYPE_RESET = const(3)
#coap content types
COAP_CONTENTFORMAT_TEXT_PLAIN = const(0)
COAP_CONTENTFORMAT_APPLICATION_LINKFORMAT = const(40)
COAP_CONTENTFORMAT_APPLICATION_XML = const(41)
COAP_CONTENTFORMAT_APPLICATION_OCTET_STREAM = const(42)
COAP_CONTENTFORMAT_APPLICATION_EXI = const(47)
COAP_CONTENTFORMAT_APPLICATION_JSON = const(50)
#COAP option value types
COAP_OPTION_TYPE_EMPTY = const(0)
COAP_OPTION_TYPE_OPAQUE = const(1)
COAP_OPTION_TYPE_UINT = const(2)
COAP_OPTION_TYPE_STRING = const(3)
#COAP options
COAP_OPTION_IF_MATCH = const(1)
COAP_OPTION_URI_HOST = const(3)
COAP_OPTION_ETAG = const(4)
COAP_OPTION_IF_NONE_MATCH = const(5)
COAP_OPTION_URI_PORT = const(7)
COAP_OPTION_LOCATION_PATH = const(8)
COAP_OPTION_URI_PATH = const(11)
COAP_OPTION_CONTENT_FORMAT = const(12)
COAP_OPTION_MAX_AGE = const(14)
COAP_OPTION_URI_QUERY = const(15)
COAP_OPTION_ACCEPT = const(17)
COAP_OPTION_LOCATION_QUERY = const(20)
COAP_OPTION_PROXY_URI = const(35)
COAP_OPTION_PROXY_SCHEME = const(39)
#COAP options registry
coapOptionsRegistry = {
        COAP_OPTION_URI_HOST: {
            'name': 'Uri-Host',
            'type': COAP_OPTION_TYPE_STRING,
            'min_size': 1,
            'max_size': 255,
            'default': None,
            'repeatable': False
        },
        COAP_OPTION_URI_PORT: {
            'name': 'Uri-Port',
            'type': COAP_OPTION_TYPE_UINT,
            'min_size': 0,
            'max_size': 2,
            'default': None,
            'repeatable': False
        },
        COAP_OPTION_URI_PATH: {
            'name': 'Uri-Path',
            'type': COAP_OPTION_TYPE_STRING,
            'min_size': 0,
            'max_size': 255,
            'default': None,
            'repeatable': True
        },
        COAP_OPTION_CONTENT_FORMAT: {
            'name': 'Content-Format',
            'type': COAP_OPTION_TYPE_UINT,
            'min_size': 0,
            'max_size': 2,
            'default': None,
            'repeatable': False
        },
        COAP_OPTION_URI_QUERY: {
            'name': 'Uri-Query',
            'type': COAP_OPTION_TYPE_STRING,
            'min_size': 0,
            'max_size': 255,
            'default': None,
            'repeatable': True
        },
        COAP_OPTION_ACCEPT: {
            'name': 'Accept',
            'type': COAP_OPTION_TYPE_UINT,
            'min_size': 0,
            'max_size': 2,
            'default': None,
            'repeatable': False
        }
    }
#COAP response codes
COAP_SUCCESS_CREATED = const(65) #2.01
COAP_SUCCESS_DELETED = const(66) #2.02
COAP_SUCCESS_VALID = const(67) #2.03
COAP_SUCCESS_CHANGED = const(68) #2.04
COAP_SUCCESS_CONTENT = const(69) #2.05
COAP_CLIENT_ERROR_BAD_REQUEST = const(128) #4.00
COAP_CLIENT_ERROR_UNAUTHORIZED = const(129) #4.01
COAP_CLIENT_ERROR_BAD_OPTION = const(130) #4.02
COAP_CLIENT_ERROR_FORBIDDEN = const(131) #4.03
COAP_CLIENT_ERROR_NOT_FOUND = const(132) #4.04
COAP_CLIENT_ERROR_METHOD_NOT_ALLOWED = const(133) #4.05
COAP_CLIENT_ERROR_NOT_ACCEPTABLE = const(134) #4.06
COAP_CLIENT_ERROR_PRECONDITION_FAILED = const(140) #4.12
COAP_CLIENT_ERROR_REQUEST_ENTITY_TOO_LARGE = const(141) #4.13
COAP_CLIENT_ERROR_UNSUPPORTED_CONTENT_FORMAT = const(143) #4.15
COAP_SERVER_ERROR_INTERNAL_SERVER_ERROR = const(160) #5.00
COAP_SERVER_ERROR_NOT_IMPLEMENTED = const(161) #5.01
COAP_SERVER_ERROR_BAD_GATEWAY = const(162) #5.02
COAP_SERVER_ERROR_SERVICE_UNAVAILABLE = const(163) #5.03
COAP_SERVER_ERROR_GATEWAY_TIMEOUT = const(164) #5.04
COAP_SERVER_ERROR_PROXYING_NOT_SUPPORTED = const(165) #5.05
#COAP message formats
COAP_PAYLOAD_MARKER = const(0xFF)
#COAP errors
class CoapMessageFormatError(Exception):
    pass

class CoapVersionError(Exception):
    pass

class CoapNotFoundError(Exception):
    pass

class CoapContentFormatError(Exception):
    pass

class CoapBadOptionError(Exception):
    pass
#CoAP Resource
class CoapResource(object):
    def __init__(self, path, server, handle_get, handle_put):
        self.title = None
        self.path = path
        self.server = server
        self.rt = None
        self.if_ = None
        self.ct = None
        self.children = []
        #handler functions - post and delete are not implemented
        self.handle_get = handle_get
        self.handle_put = handle_put

    def addChild(self, child):
        child.path = self.path + '/' + child.path
        self.children.append(child)
        self.server.addResource(child)

    def removeChild(self, child):
        self.children.remove(child)
        self.server.deleteResource(child)

    def getChildren(self, child):
        return self.children

    def removeChildren(self):
        for r in self.children:
            self.server.deleteResource(r.path)
        self.children = []

    def get(self, *args, **kwargs):
        try:
            return CoapPayload(*self.handle_get(*args, **kwargs))
        except TypeError:
            #no handler function was passed
            return CoapPayload('Not Implemented', 0)

    def put(self, *args, **kwargs):
        try:
            return CoapPayload(*self.handle_put(*args, **kwargs))
        except TypeError:
            #no handler function was passed
            return CoapPayload('Not Implemented', 0)

class WellKnownCore(CoapResource):
    def __init__(self, server):
        super().__init__('.well-known/core', server, None, None)

    def get(self, *args, **kwargs):
        return CoapPayload(self.server.getResourcesInCoRELinkFormat(), 40)

class CoapOption(object):
    def __init__(self, number, value):
        self.number = number
        self.value = value

        if not self.number in coapOptionsRegistry:
            raise CoapUnknownOptionError()

    def length(self):
        if self.type() == COAP_OPTION_TYPE_EMPTY:
            return 0
        elif self.type() == COAP_OPTION_TYPE_OPAQUE:
            return len(self.value)
        elif self.type() == COAP_OPTION_TYPE_UINT:
            #calc minimum number of bytes needed to represent this integer
            length = 0
            int_val = int(self.value)
            while int_val:
                int_val >>= 8
                length += 1
            if length > 4:
                #unzulässig
                pass
            return length
        elif self.type() == COAP_OPTION_TYPE_STRING:
            return len(bytes(self.value, 'utf-8'))

    def type(self):
        return coapOptionsRegistry[self.number]['type']

    def is_critical(self):
        return bool(self.value & 1)

    def is_unsafe(self):
        return bool(self.number & 2)

    def __lt__(self, other):
        #overload '<' operator to sort options
        return self.number < other.number

#CoAP payload
class CoapPayload(object):
    def __init__(self, payload, content_format):
        self.data = payload
        self.content_format = content_format

#CoAP Message
class CoapMessage(object):
    @classmethod
    def deserialize(cls, dgram):
        msg = cls()
        datagram = dgram
        dgram_len = len(datagram)
        pos = 0
        running_delta = 0
        datagram_deserialization_complete = False

        if dgram_len < 4:
            #Header must have at least 4 bytes
            raise CoapMessageFormatError('CoAP message has a length of less than 4 bytes')
        elif dgram_len == 4 and struct.unpack_from('!B', datagram, 2)[0] == 0:
            header = struct.unpack_from('!BBH', datagram, pos)
            pos += 4

            msg.ver = (header[0] & 0b11000000) >> 6
            if msg.ver != 1:
                raise CoapVersionError('coap version is not 1')
            msg.t   = (header[0] & 0b00110000) >> 4
            msg.tkl = (header[0] & 0b00001111) >> 0

            msg.code = header[1]
            msg.mid = header[2]

            return CoapEmpty(msg)
        elif dgram_len > 4:
            header = struct.unpack_from('!BBH', datagram, pos)
            pos += 4

            msg.ver = (header[0] & 0b11000000) >> 6
            if msg.ver != 1:
                raise CoapVersionError('coap version is not 1')
            msg.t   = (header[0] & 0b00110000) >> 4
            msg.tkl = (header[0] & 0b00001111) >> 0

            msg.code = header[1]
            if msg.code == 0:
                raise CoapMessageFormatError('message of type Empty has more than 4 bytes')
            msg.mid = header[2]

            if msg.tkl > 0:
                fmt = '!{0}s'.format(msg.tkl)
                msg.token = struct.unpack_from(fmt, datagram, pos)[0]
                pos += msg.tkl

            while not datagram_deserialization_complete:
                try:
                    next_byte = struct.unpack_from('!B', datagram, pos)
                    pos += 1
                except:
                    #print('Ende erreicht')
                    datagram_deserialization_complete = True
                    break

                if next_byte != COAP_PAYLOAD_MARKER:
                    option_header = next_byte
                    option_delta = (option_header[0] & 0xF0) >> 4
                    option_length = option_header[0] & 0x0F

                    if option_delta == 13:
                        delta = struct.unpack_from('!B', datagram, pos)[0] + 13
                        pos += 1
                    elif option_delta == 14:
                        delta = struct.unpack_from('!B', datagram, pos)[0] + 269
                        pos += 1
                    elif option_delta == 15:
                        raise CoapMessageFormatError('option number must not be 15')
                    else:
                        delta = option_delta

                    option_number = delta + running_delta
                    running_delta += delta

                    if option_length == 13:
                        length = struct.unpack_from('!B', datagram, pos)[0] + 13
                        pos += 1
                    elif option_length == 14:
                        length = struct.unpack_from('!B', datagram, pos)[0] + 269
                        pos += 1
                    elif option_length == 15:
                        raise CoapMessageFormatError('option length must not be 15')
                    else:
                        length = option_length

                    fmt = '!{0}s'.format(length)
                    option_value = struct.unpack_from(fmt, datagram, pos)[0]
                    pos += length

                    msg.options.append(CoapOption(option_number, option_value))
                else:
                    try:
                        fmt = '!{0}s'.format(dgram_len - pos)
                        msg.payload = struct.unpack_from(fmt, datagram, pos)
                        datagram_deserialization_complete = True
                    except:
                        raise CoapMessageFormatError('Payload too short')
            else:
                raise CoapMessageFormatError('non-empty message has only 4 bytes length')

        return CoapRequest(msg)

    @classmethod
    def serialize(cls, response):
        msg = cls()

        msg.ver = response.ver
        msg.t = response.t
        if response.token:
            msg.tkl = len(response.token)
        else:
            msg.tkl = 0

        msg.code = response.code
        msg.mid = response.mid

        msg.token = response.token
        msg.options = response.options

        msg.payload = response.payload

        return msg.to_bytes()

    def __init__(self):
        self.ver = 1
        self.t = 1
        self.tkl = 0

        self.token = None
        self.options = [] #must be sorted by option values!!!

        self.payload = None

    def to_bytes(self, content_format=COAP_CONTENTFORMAT_TEXT_PLAIN):
        values = []
        fmt = '!BBH'
        values.append((self.ver << 6) | (self.t << 4) | self.tkl)
        values.append(self.code)
        values.append(self.mid)
        if self.token:
            fmt += '{0}s'.format(self.tkl)
            values.append(self.token)
        if self.options:
            running_delta = 0
            for option in self.options:
                option_number = option.number
                option_value = option.value
                option_delta = option_number - running_delta
                option_length = option.length()

                if option_delta < 13:
                    fmt += 'B'
                    delta = option_delta
                    ext_delta = 0
                elif 12 < option_delta < 269:
                    fmt += 'BB'
                    delta = 13
                    ext_delta = option_delta - 13
                elif 268 < option_delta:
                    fmt += 'BB'
                    delta = 14
                    ext_delta = option_delta - 269
                else:
                    raise CoapMessageFormatError('option number too high')
                running_delta += option_number

                if option_length < 13:
                    length = option_length
                    ext_length = 0
                elif 12 < option_length < 269:
                    fmt += 'B'
                    length = 13
                    ext_length = option_length - 13
                elif 268 < option_length:
                    fmt += 'B'
                    length = 14
                    ext_length = option_length - 269
                else:
                    raise CoapMessageFormatError('option length too long')

                values.append((delta << 4) | length)

                if ext_delta:
                    values.append(ext_delta)
                if ext_length:
                    values.append(ext_length)
                if option_value and option_length:
                    if option.type() == COAP_OPTION_TYPE_OPAQUE:
                        fmt += '{0}B'.format(option_length)
                        values.append(option_value)
                    elif option.type() == COAP_OPTION_TYPE_UINT:
                        fmt += '{0}B'.format(option_length)
                        values.append(option_value)
                    elif option.type() == COAP_OPTION_TYPE:
                        fmt += '{0}s'.format(option_length)
                        values.append(bytes(str(option_value), 'utf-8'))
                    else:
                        pass

        if self.payload:
            fmt += 'B'
            values.append(COAP_PAYLOAD_MARKER)
            if content_format == COAP_CONTENTFORMAT_TEXT_PLAIN:
                data = str(self.payload).encode('utf-8')
            elif content_format == COAP_CONTENTFORMAT_APPLICATION_EXI:
                raise CoapContentFormatError('content format exi is not supported')
            elif content_format == COAP_CONTENTFORMAT_APPLICATION_XML:
                data = str(self.payload).encode('utf-8')
            elif content_format == COAP_CONTENTFORMAT_APPLICATION_JSON:
                data = json.dumps(self.payload)
            elif content_format == COAP_CONTENTFORMAT_APPLICATION_LINKFORMAT:
                data = str(self.payload).encode('utf-8')
            elif content_format == COAP_CONTENTFORMAT_APPLICATION_OCTET_STREAM:
                data = self.payload
            else:
                raise CoapContentFormatError('content format {} is unknown'.format(content_format))
            fmt += '{0}s'.format(len(data))
            values.append(data)

        return struct.pack(fmt, *values)

class CoapRequest(object):
    def __init__(self, msg):
        self.ver = msg.ver
        self.t = msg.t
        self.code = msg.code
        self.mid = msg.mid

        self.token = msg.token
        self.options = msg.options
        self.payload = msg.payload

    def method(self):
        return self.code & 0b00011111

    def content_format(self):
        for option in self.options:
            if option.number == COAP_OPTION_CONTENT_FORMAT:
                return int(option.value)
        return False

    def uri_host(self):
        for option in self.options:
            if option.number == COAP_OPTION_URI_HOST:
                return str(option.value, 'utf-8')
        return False

    def uri_port(self):
        for option in self.options:
            if option.number == COAP_OPTION_URI_PORT:
                return str(option.value, 'utf-8')
        return False

    def uri_path(self):
        paths = []
        for option in self.options:
            if option.number == COAP_OPTION_URI_PATH:
                paths.append(str(option.value, 'utf-8'))
        return '/'.join(paths)

    def uri_queries(self):
        queries = []
        for option in self.options:
            if option.number == COAP_OPTION_URI_QUERY:
                queries.append(str(option.value, 'utf-8'))
        return queries

    def url(self):
        prot = 'coap'
        host = self.uri_host() or 'localhost'
        port = self.uri_port() or '5683'
        path = self.uri_paths() or ''
        query = '&'.join(self.uri_queries()) or ''

        return prot + '://' + host + ':' + port + '/' + path + '?' + query

class CoapResponse(object):
    def __init__(self):
        self.ver = 1
        self.t = None
        self.tkl = 0
        self.code = None
        self.mid = None

        self.token = None
        self.options = []
        self.payload = None

    def add_option(self, option_number, option_value):
        self.options.append(CoapOption(option_number, option_value))
        self.options.sort()

    def content_format(self, cf):
        if self.payload:
            self.add_option(COAP_OPTION_CONTENT_FORMAT, cf)

class CoapEmpty(object):
    def __init__(self, msg):
        self.ver = msg.ver
        self.t = msg.t
        self.tkl = 0
        self.code = 0
        self.mid = msg.mid

#CoAP Server
class CoapServer(object):
    def __init__(self, ip, port=5683):
        self.ip = ip
        self.port = port
        self.addr = (self.ip, self.port)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.observers = {}
        self.resources = {}

    def start(self):
        self.addResource(WellKnownCore(self))
        self.udp_sock.bind(self.addr)
        self.loop()

    def addResource(self, resource):
        self.resources[resource.path] = resource

    def deleteResource(self, uri):
        self.resources.pop(uri).deleteChildren()

    def getResource(self, uri):
        return self.resources[uri]

    def resourceExists(self, uri):
        return bool(uri in self.resources.keys())

    def getResourcesInCoRELinkFormat(self):
        #return all resources registered in core link format as specified
        #in rfc6690, section 2.1
        link_value_list = []
        for key in self.resources.keys():
            #besser: Objekte in Liste, Pfad abgleichen (Multicast)
            resource = self.resources[key]
            link_param_list = []

            if resource.rt:
                link_param_list.append("rt=\"" + resource.rt + "\"")
            if resource.if_:
                link_param_list.append("if=\"" + resource.if_ + "\"")
            if resource.title:
                link_param_list.append("title=\"" + resource.title + "\"")
            if resource.ct:
                link_param_list.append("ct=" + resource.ct)

            link_params = ';'.join(link_param_list)
            if link_params:
                link_value = "<" + resource.path + ">;" + link_params
            else:
                link_value = "<" + resource.path + ">"
            link_value_list.append(link_value)
        return ','.join(link_value_list)

    def loop(self):
        print('Server started...')
        while True:
            datagram, addr = self.udp_sock.recvfrom(1152)
            coap_req = CoapMessage.deserialize(datagram)

            coap_resp = self.handle_request(coap_req)

            coap_msg = CoapMessage.serialize(coap_resp)
            self.send_msg(coap_msg, addr)

    def handle_request(self, request):
        payload = None
        uri_path = request.uri_path() or None
        uri_query = request.uri_queries()
        if not uri_path:
            response = self.make_response(request, None, COAP_CLIENT_ERROR_BAD_REQUEST)
            return response
        if uri_query:
            kwargs = {q.split('=')[0]: q.split('=')[1] for q in uri_query}
        else:
            kwargs = {}

        if request.content_format():
            content_format = request.content_format()
            kwargs['content_format'] = content_format

        if request.method() == COAP_METHOD_GET:
            try:
                payload = self.getResource(uri_path).get(**kwargs)
                rc = COAP_SUCCESS_CONTENT
            except CoapNotFoundError:
                payload = CoapPayload('Not Foundd', 0)
                rc = COAP_CLIENT_ERROR_NOT_FOUND
            except:
                payload = CoapPayload('Internal Server Error', 0)
                rc = COAP_SERVER_ERROR_INTERNAL_SERVER_ERROR
        elif request.method() == COAP_METHOD_PUT:
            try:
                payload = self.getResource(uri_path).put(**kwargs)
                rc = COAP_SUCCESS_CREATED
            except CoapNotFoundError:
                payload = CoapPayload('Not Foundd', 0)
                rc = COAP_CLIENT_ERROR_NOT_FOUND
            except:
                payload = CoapPayload('Internal Server Error', 0)
                rc = COAP_SERVER_ERROR_INTERNAL_SERVER_ERROR
        elif request.method() == COAP_METHOD_POST:
            payload = CoapPayload('Not Implemented', 0)
            rc = COAP_SERVER_ERROR_NOT_IMPLEMENTED
        elif request.method() == COAP_METHOD_DELETE:
            payload = CoapPayload('Not Implemented', 0)
            rc = COAP_SERVER_ERROR_NOT_IMPLEMENTED
        else:
            payload = CoapPayload('Bad Request', 0)
            rc = COAP_CLIENT_ERROR_BAD_REQUEST

        return self.make_response(request, payload, rc)

    def make_response(self, request, payload, rc):
        response = CoapResponse()

        if request.t == COAP_TYPE_CONFIRMABLE:
            response.t = COAP_TYPE_ACKNOWLEDGEMENT
        elif request.t == COAP_TYPE_NON_CONFIRMABLE:
            response.t = COAP_TYPE_NON_CONFIRMABLE
        else:
            #bad message type
            pass

        response.code = rc
        response.mid = request.mid
        response.token = request.token

        response.payload = payload.data
        response.content_format(payload.content_format)

        return response

    def send_msg(self, datagram, destination):
        #datagram = coap_msg.to_bytes()
        self.udp_sock.sendto(datagram, destination)
