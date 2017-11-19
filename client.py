# chat_client.py

import sys
import socket
import select
 
logged_in = False

def start_client():
	global logged_in

	if(len(sys.argv) < 3) :
		print 'Usage : python chat_client.py hostname port'
		sys.exit()

	host = sys.argv[1]
	port = int(sys.argv[2])
	 
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.settimeout(2)
	 
	# connect to remote host
	try :
		s.connect((host, port))
	except :
		print 'Unable to connect'
		sys.exit()
	 
	print 'Connected to remote host. You can start sending messages'
	sys.stdout.write('[Me] '); sys.stdout.flush()
	 
	while 1:
		socket_list = [sys.stdin, s]
		 
		# Get the list sockets which are readable
		ready_to_read,ready_to_write,in_error = select.select(socket_list , [], [])
		 
		for sock in ready_to_read:             
			if sock == s:
				# incoming message from remote server, s
				data = sock.recv(4096)
				if not data :
					print '\nDisconnected from chat server'
					sys.exit()
				else :
					#print data
					sys.stdout.write(data + "\n")
					data_split = data.split(" ")
					command = data_split[0]

					if command == "connect":
						if data_split[1] == '0':
							logged_in = True
							print logged_in

					sys.stdout.flush()     
			
			else :
				# user entered a message
				msg = sys.stdin.readline()
				# create username password -> creates an account
				# connect username password -> connects to server
				# send user_to_send msg -> sends the message msg to the user user_to_send
				s.send(msg[:-1]) # without enter
				sys.stdout.write('[Me] '); sys.stdout.flush() 

if __name__ == "__main__":

	sys.exit(start_client())