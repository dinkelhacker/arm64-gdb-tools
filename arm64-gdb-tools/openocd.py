import socket

class OpenOcd:
    COMMAND_TOKEN = '\x1a'
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.tclRpcIp       = "127.0.0.1"
        self.tclRpcPort     = 6666
        self.bufferSize     = 4096

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.sock.connect((self.tclRpcIp, self.tclRpcPort))

    def disconnect(self):
        try:
            self.send("exit")
        finally:
            self.sock.close()

    def send(self, cmd):
        """Send a command string to TCL RPC. Return the result that was read."""
        data = (cmd + OpenOcd.COMMAND_TOKEN).encode("utf-8")
        if self.verbose:
            print("<- ", data)

        self.sock.send(data)
        return self._recv()

    def _recv(self):
        """Read from the stream until the token (\x1a) was received."""
        data = bytes()
        while True:
            chunk = self.sock.recv(self.bufferSize)
            data += chunk
            if str(OpenOcd.COMMAND_TOKEN).encode("utf-8") in chunk:
                break

        if self.verbose:
            print("-> ", data)

        data = data.decode("utf-8").strip()
        data = data[:-1] # strip trailing \x1a

        return data
        
    def _mrs(self, cr0, cr1, crn, crm, op2):
    	output = self.send("aarch64 mrs {} {} {} {} {}".format(cr0, cr1, crn, crm, op2))
        return output.split(": ")[1]

    def read_phys_memory(self, wordLen, address, n):
        output = self.send("read_memory 0x%x %d %d phys" % (address, wordLen, n))
        return map(lambda x: int(x, 16), output.split(" "))