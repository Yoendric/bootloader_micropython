import network
import time
import upip
import usocket
import gc
import os
import machine

def connect_wifi(essid,password):
  station = network.WLAN(network.STA_IF)
  if station.isconnected() == True:
    print("Already connected")
    return
  station.active(True)
  station.connect(essid, password)
  while station.isconnected() == False:
    print ("Aun no conectado")
    time.sleep(1)
  print("Connection successful")
  print(station.ifconfig())
  return 
  
class Response:
    def __init__(self, f):
        self.raw = f
        self.encoding = 'utf-8'
        self._cached = None

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        self._cached = None

    @property
    def content(self):
        if self._cached is None:
            try:
                self._cached = self.raw.read()
            finally:
                self.raw.close()
                self.raw = None
        return self._cached

    @property
    def text(self):
        return str(self.content, self.encoding)

    def json(self):
        import ujson
        return ujson.loads(self.content)
 
class HttpClient:

    def request(self, method, url, data=None, json=None, headers={}, stream=None):
        try:
            proto, dummy, host, path = url.split('/', 3)
        except ValueError:
            proto, dummy, host = url.split('/', 2)
            path = ''
        if proto == 'http:':
            port = 80
        elif proto == 'https:':
            import ussl
            port = 443
        else:
            raise ValueError('Unsupported protocol: ' + proto)

        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)

        ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
        ai = ai[0]

        s = usocket.socket(ai[0], ai[1], ai[2])
        try:
            s.connect(ai[-1])
            if proto == 'https:':
                s = ussl.wrap_socket(s, server_hostname=host)
            s.write(b'%s /%s HTTP/1.0\r\n' % (method, path))
            if not 'Host' in headers:
                s.write(b'Host: %s\r\n' % host)
            # Iterate over keys to avoid tuple alloc
            for k in headers:
                s.write(k)
                s.write(b': ')
                s.write(headers[k])
                s.write(b'\r\n')
            # add user agent
            s.write('User-Agent')
            s.write(b': ')
            s.write('MicroPython OTAUpdater')
            s.write(b'\r\n')
            if json is not None:
                assert data is None
                import ujson
                data = ujson.dumps(json)
                s.write(b'Content-Type: application/json\r\n')
            if data:
                s.write(b'Content-Length: %d\r\n' % len(data))
            s.write(b'\r\n')
            if data:
                s.write(data)

            l = s.readline()
            # print(l)
            l = l.split(None, 2)
            status = int(l[1])
            reason = ''
            if len(l) > 2:
                reason = l[2].rstrip()
            while True:
                l = s.readline()
                if not l or l == b'\r\n':
                    break
                # print(l)
                if l.startswith(b'Transfer-Encoding:'):
                    if b'chunked' in l:
                        raise ValueError('Unsupported ' + l)
                elif l.startswith(b'Location:') and not 200 <= status <= 299:
                    raise NotImplementedError('Redirects not yet supported')
        except OSError:
            s.close()
            raise

        resp = Response(s)
        resp.status_code = status
        resp.reason = reason
        return resp

    def head(self, url, **kw):
        return self.request('HEAD', url, **kw)

    def get(self, url, **kw):
        return self.request('GET', url, **kw)

    def post(self, url, **kw):
        return self.request('POST', url, **kw)

    def put(self, url, **kw):
        return self.request('PUT', url, **kw)

    def patch(self, url, **kw):
        return self.request('PATCH', url, **kw)

    def delete(self, url, **kw):
        return self.request('DELETE', url, **kw)

def download_file(url, path):
  print('\tDownloading: ', path)
  http_client = HttpClient()
  with open(path, 'w') as outfile:
    try:
      response = http_client.get(url)
      outfile.write(response.text)
    finally:
      response.close()
      outfile.close()
      gc.collect()

def write_main_file(function):
  data='def start():\n  import main.{nombre} as MAIN\n  MAIN.main()\n  \ndef boot():   \n  start()\n\nboot()\n'.format(nombre=function)
  with open('main.py', 'w') as outfile:
    try:
      outfile.write(data)
    finally:
      outfile.close()
  
def main():
  connect_wifi("ESSID_XXXXX","PASSWORD_XXXXXX") #Datos de la contraseña y Essid
  url ='https://github.com/name_repository/name_project'    #URL de github code
  function = 'xxxxxxxxxxxxx' #function principal del proyecto donde esta el main() 
  http_client = HttpClient()
  os.mkdir('main')
  github_repo=url.rstrip('/').replace('https://github.com', 'https://api.github.com/repos')
  root_url=github_repo + '/contents/main'
  file_list = http_client.get(root_url)
  for file in file_list.json():
    if file['type'] == 'file':
      download_url = file['download_url']
      download_file(download_url,file['path'])
  try:
    f=open('main/requirements.txt','r')
    req=f.read().split('\n')
    for i in req:
      upip.install(i)
  except:
    print("No requirements library extern")
  finally:
    f.close()
  write_main_file(function)
  os.remove('programacion.py')
  machine.reset()
  return
  
main()  
