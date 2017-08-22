# COAPython
a lightweight coap implementation for micropython (esp8266 port)

!!!warning!!! this implementation works for me, but is still in progress
____________________________________________________________________________

Creating a new Resource:\n
    \nresource = CoapResource(path-name, server, handle get, handle put)
    \nserver.addResource(resource)
\n\n    
Starting the server:\n
    server = CoapServer(ip, port)\n
    server.start()
