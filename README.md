# COAPython
a lightweight coap implementation for micropython (esp8266 port)

!!!warning!!! this implementation works for me, but is still in progress
____________________________________________________________________________

Creating a new Resource:  
    resource = CoapResource(path-name, server, handle get, handle put)  
    server.addResource(resource)  
    
Starting the server:  
    server = CoapServer(ip, port)  
    server.start()
