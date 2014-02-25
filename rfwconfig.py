import logging, sys, types, os.path, re, config

class RfwConfig(config.Config):

    def __init__(self, path):
        config.Config.__init__(self, path)
        self._whitelist = None
        
        # Fail early validations. Read all properties to validate and show config dependencies
        if self.is_outward_server():
            self.outward_server_port()
            self.outward_server_ip()
            self.outward_server_certfile()
            self.outward_server_keyfile()
        if self.is_local_server():
            self.local_server_port()
            self.is_local_server_authentication()
        self.is_non_restful()
        if self.is_outward_server() or self.is_local_server_authentication():
            self.auth_username()
            self.auth_password()
        self.chain_input_action()
        self.chain_output_action()
        self.chain_forward_action()
        self.whitelist_file()
        self.whitelist()  # it will also cache the whitelist result
            
 
    # Check if the IP address range is correct in CIDR format: xxx.xxx.xxx.xxx/nn
    # If allow_no_mask = True it accepts also individual IP address without network mask
    # return validated (and trimmed) IP address range or False if not valid
    def _validate_ip_cidr(self, ip, allow_no_mask=False):
        if not ip:
            return False
        ip = ip.strip()
        m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(/(\d{1,2})$|$)", ip)
        mask = m.group(6)
        if m:
            if int(m.group(1)) < 256 and int(m.group(2)) < 256 and int(m.group(3)) < 256 and int(m.group(4)) < 256:
                if mask and int(mask) >= 0 and int(mask) <= 32:
                    return ip
                if allow_no_mask and not mask:
                    return ip
        return False

    # Check if the IP address has correct format.
    # return validated (and trimmed) IP address or False if not valid
    def _validate_ip(self, ip):
        possibly_with_mask = self._validate_ip_cidr(self, ip, allow_no_mask=True)
        if not '/' in possibly_with_mask:
            return possibly_with_mask
        return False




    # Port number format validator
    # return validated port number as string or False if not valid
    def _validate_port(self, port):
        if not port:
            return False
        port = port.strip()
        if port.isdigit() and int(port) > 0 and int(port) < 65536:
            return port
        return False


    def is_outward_server(self):
        return self._getflag("outward.server", "outward.server not enabled. Ignoring outward.server.port and outward.server.ip if present.")
    
    def outward_server_port(self):
        if self.is_outward_server():
            try:
                port = self._get("outward.server.port")
                if port and self._validate_port(port):
                    return port
                else:
                    self._configexit("Wrong outward.server.port value. It should be a single number from the 1..65535 range")
            except NoOptionError, e:
                self._configexit(str(e))
        else:
            msg = "outward.server.port read while outward.server not enabled"
            self._configexit(msg)
    
    
    def outward_server_ip(self):
        if self.is_outward_server():
            try:
                return self._get("outward.server.ip")
            except NoOptionError, e:
                self._configexit(str(e))
        else:
            msg = "outward.server.ip read while outward.server not enabled"
            self._configexit(msg)
    
    def outward_server_certfile(self):
        if self.is_outward_server():
            return self._getfile("outward.server.certfile")
        else:
            msg = "outward.server.certfile read while outward.server not enabled"
            self._configexit(msg)
 

    def outward_server_keyfile(self):
        if self.is_outward_server():
            return self._getfile("outward.server.keyfile")
        else:
            msg = "outward.server.keyfile read while outward.server not enabled"
            self._configexit(msg)


    def is_local_server(self):
        return self._getflag("local.server", "local.server not enabled. Ignoring local.server.port if present.")
    
    
    def local_server_port(self):
        if self.is_local_server():
            try:
                port = self._get("local.server.port")
                if port and self._validate_port(port):
                    return port
                else:
                    self._configexit("Wrong local.server.port value. It should be a single number from the 1..65535 range")
            except NoOptionError, e:
                self._configexit(str(e))
        else:
            msg = "local.server.port read while local.server not enabled"
            self._configexit(msg)
    
    def is_non_restful(self):
        return self._getflag("non.restful")
    
    def is_local_server_authentication(self):
        if self.is_local_server():
            try:
                return self._getflag("local.server.authentication")
            except NoOptionError, e:
                self._configexit(str(e))
        else:
            msg = "local.server.authentication read while local.server not enabled"
            self._configexit(msg)
    
    
    def auth_username(self):
        if self.is_outward_server() or self.is_local_server_authentication():
            try:
                username = self._get("auth.username")
                if username:
                    return username
                else:
                    self._configexit("auth.username cannot be empty")
            except NoOptionError, e:
                self._configexit(str(e))
        else:
            msg = "auth.username read while outward.server not enabled and local.server.authentication not enabled"
            self._configexit(msg)
    
    
    def auth_password(self):
        if self.is_outward_server() or self.is_local_server_authentication():
            try:
                password = self._get("auth.password")
                if password:
                    return password
                else:
                    self._configexit("auth.password cannot be empty")
            except NoOptionError, e:
                self._configexit(str(e))
        else:
            msg = "auth.password read while outward.server not enabled and local.server.authentication not enabled"
            self._configexit(msg)
   
    def _chain_action(self, name):
        try:
            action = self._get(name)
            if action:
                action = action.upper()
                if action in ['DROP', 'ACCEPT']:
                    return action
                self._configexit("allowed values for {} are DROP or ACCEPT".format(name))
            else:
                self._configexit("{} cannot be empty. Allowed values are DROP or ACCEPT".format(name))
        except NoOptionError, e:
            self._configexit(str(e))


    def chain_input_action(self):
        return self._chain_action('chain.input.action')

    def chain_output_action(self):
        return self._chain_action('chain.output.action')

    def chain_forward_action(self):
        return self._chain_action('chain.forward.action')

   
    def whitelist_file(self):
        return self._getfile("whitelist.file")


    # return cached list of whitelist IP address ranges in CIDR format or individual IP addresses.
    # TODO allow IP ranges with hyphen, cidrize all including individual IPs
    def whitelist(self):
        #TODO not thread safe but this method is initialized from constructor so it should be fine
        if self._whitelist is None:
            wfile = self.whitelist_file()
            with open(wfile) as f:
                lines = f.readlines()
            #TODO allow IP ranges: xxx.xxx.xxx.xxx-yyy.yyy.yyy.yyy - need to cidrize, see IpNet.php
            ips = [self._validate_ip_cidr(line, allow_no_mask=True) for line in lines if line.strip() and not line.strip().startswith('#')]
            if False in ips:
                self._configexit("Wrong IP address format in {}".format(wfile))
            if not ips:
                self._configexit("Could not find a valid IP address in {}".format(wfile))
            self._whitelist = ips
        return self._whitelist



# test particular config file. Results must be compared manually
if __name__ == "__main__":

    #TODO write more generic tests
    rfwconf = RfwConfig("rfw.conf")

    print(rfwconf.auth_password())

    module = sys.modules[__name__]
    # take all attributes of the module
    attrs = [getattr(module, name, None) for name in dir()]
    # filter for function without arguments
    #fs = filter(lambda a: isinstance(a, types.FunctionType) and a.func_code.co_argcount == 0, attrs)
    fs = [a for a in attrs if isinstance(a, types.FunctionType) and a.func_code.co_argcount == 0]
    for f in fs:
        print("%s = %s" % (f.__name__, f()))



