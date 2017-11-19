# chat_server.py
 
import sys
import socket
import select
import MySQLdb

HOST = '' 
SOCKET_LIST = []
RECV_BUFFER = 4096 
PORT = 8888


# Credentials for database
hostDb = "localhost"
userDb ="root"      
passwdDb = "root"
dbName = "runningApp"


# Dict of pairs <Username, Socket>
connections = {}

# Returns the db response to the given query
def query_database(query):
	db = MySQLdb.connect(host = hostDb, 
                     user = userDb, 
                     passwd = passwdDb,
                     db = dbName)
	cursor = db.cursor()

	cursor.execute(query)
	res = cursor.fetchall()
	db.close()
	return res

# Returns the db response to the given query
def query_database_values(query, values):
	db = MySQLdb.connect(host = hostDb, 
                     user = userDb, 
                     passwd = passwdDb,
                     db = dbName)
	cursor = db.cursor()

	cursor.execute(query, values)
	res = cursor.fetchall()
	db.close()
	return res

# Inserts values into db 
def insert_database(query, values):
	db = MySQLdb.connect(host = hostDb, 
                     user = userDb, 
                     passwd = passwdDb,
                     db = dbName)
	cursor = db.cursor()

	try:
		cursor.execute(query, values)
		db.commit()
		db.close()
		return 0
	except Exception as e: 
		print e
		db.rollback()
		db.close()
		return 1

# 0 -> success
# 1 -> user already exists
# 2 -> error with db
def register_user(username, password):
	query = "select username from credentials"
	res = query_database(query)
	for user in res:
		if username == user[0]:
			return 1
	query = "insert into credentials values(%s, %s)"
	values = (username, password)
	res = insert_database(query, values)
	if res == 0:
		return 0
	return 2


# 0 -> success
# 1 -> wrong password
# 2 -> invalid username
# 3 -> user already logged in
def login(username, password):
	if username in connections.keys():
		return 3

	query = "select * from credentials"
	res = query_database(query)
	for (user, passwd) in res:
		if user == username:
			if passwd == password:
				return 0
			else:
				return 1
	return 2

# Remove username from connections and sends a list of online matches to his online matches
def logout(username):
	global connections
	sock = get_connection_by_user(username)
	connections.pop(username)
	
	my_match_users = get_online_matches_user(username)
	for user in my_match_users:
		online_matches = get_online_matches_user(user)
		sock = connections[user]
		if sock != None:
			msg = "recv_online_matches "
			for user2 in online_matches:
				msg += str(user2) + " "
			sock.send(msg)

# Returns a list of online users that match with username
def get_online_matches_user(username):
	global connections
	users = []
	matches = get_matches(username)
	user_matches = []
	for (user, time, place) in matches:
		if user not in user_matches and user in connections.keys():
			user_matches.append(user)
	return user_matches

# Returns a list users that match with username
def get_matches_user(username):
	global connections
	users = []
	matches = get_matches(username)
	user_matches = []
	for (user, time, place) in matches:
		if user not in user_matches:
			user_matches.append(user)
	return user_matches

# 0 -> success
# 1 -> error to db
def register_running(username, time, place):
	query = "select max(id_running) from runnings"
	res = query_database(query)
	print res[0][0]
	id_running = int(res[0][0]) + 1
	query = "insert into runnings values(%s, %s, %s, %s)"
	values = (id_running, username, time, place)
	res = insert_database(query, values)
	print res
	return res

# Find all matches for the current running, insert them in db and return them
def find_running_matches(username, my_time, my_place):
	query = "select * from runnings"
	runnings = query_database(query)

	query = "select id_running from runnings where username = %s and time = %s and place = %s"
	values = (username, my_time, my_place)
	res = query_database_values(query, values)
	print res
	my_id = res[0][0]
	user_matches = []
	for (id_running, user, time, place) in runnings:
		if user != username:
			if check_time(my_time, time) and check_place(my_place, place):
				user_matches.append((user, time, place))
				# Insert the match in matches table if not already there
				query = "select id_running1, id_running2 from matches"
				matches = query_database(query)
				exists_match = False
				for (id_running1, id_running2) in matches:
					if (id_running1 == my_id and id_running2 == id_running) or (id_running1 == id_running and id_running2 == my_id):
						exists_match = True
						break
				if not exists_match:
					id_match = len(matches) + 1
					query = "insert into matches values(%s, %s, %s)"
					values = (id_match, my_id, id_running)
					res = insert_database(query, values)				
	return user_matches

# Returns a list of touples of form: (user_matched, his_time, his_place)
def get_matches(username):
	query = "select * from runnings"
	runnings = query_database(query)

	matches = []
	my_runnings = []
	for (id_running, user, time, place) in runnings:
		if user == username:
			my_runnings.append((id_running, time, place))

	for (id_running, user, time, place) in runnings:
		if user != username:
			for (my_id, my_time, my_place) in my_runnings:
				if check_time(my_time, time) and check_place(my_place, place):
					matches.append((user, time, place))
						
	return matches


#TODO 
def check_time(time1, time2):
	return True

#TODO
def check_place(place1, place2):
	return True

# Returns the user connected to the socket 
def get_user_by_connection(socket):
	global connections
	for user in connections.keys():
		if connections[user] == socket:
			return user
	return ""

# Returns the socket of the connected user 
def get_connection_by_user(user):
	global connections
	if user in connections.keys():
		return connections[user]
	return None

def start_server():

	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server_socket.bind((HOST, PORT))
	server_socket.listen(10)
 
	# add server socket object to the list of readable connections
	SOCKET_LIST.append(server_socket)
 
	print "Chat server started on port " + str(PORT)
 
	while 1:

		# get the list sockets which are ready to be read through select
		# 4th arg, time_out  = 0 : poll and never block
		ready_to_read,ready_to_write,in_error = select.select(SOCKET_LIST,[],[],0)
	  
		for sock in ready_to_read:
			# a new connection request recieved
			if sock == server_socket: 
				sockfd, addr = server_socket.accept()
				SOCKET_LIST.append(sockfd)
				print "Client (%s, %s) connected" % addr
				 
				#broadcast(server_socket, sockfd, "[%s:%s] entered our chatting room\n" % addr)
			 
			# a message from a client, not a new connection
			else:
				# process data recieved from client, 
				# receiving data from the socket.
				data = sock.recv(RECV_BUFFER)
				if data:
					# there is something in the socket

					# create username password -> creates an account
					# login username password -> connects to server
					# rr time place -> registers a running for time and place
					# send user_to_send msg -> sends the message msg to the user user_to_send
					data_split = data.split(" ")
					command = data_split[0]

					if command == "create":
						username = data_split[1]
						password = data_split[2]
						res = register_user(username, password)
						sock.send("create " + str(res))
						continue

					if command == "login":
						username = data_split[1]
						password = data_split[2]
						res = login(username, password)
						if res == 0:
							global connections
							connections[username] = sock
							sock.send(str(res))

							matches_list = get_online_matches_user(username)
							msg = "recv_online_matches "

							for user in matches_list:
								msg += str(user) + " "
							print msg
							sock.send(msg)

							for user in matches_list:
								user_matches = get_online_matches_user(user)
								msg = "recv_online_matches "

								sock = connections[user]
								for user_match in user_matches:
									msg += str(user_match) + " "
								print msg
								sock.send(msg)
						continue
					
					if command == "logout":
						username = get_user_by_connection(sock)
						logout(username)
						continue

					if command == "rr":
						username = get_user_by_connection(sock)
						time = data_split[1]
						place = data_split[2]
						res = register_running(username, time, place)

						matches = find_running_matches(username, time, place)
						print "matches" + str(matches)
						if matches != []:
							for (m_user, m_time, m_place) in matches:
								sock.send("New Match with " + m_user + " for time " + m_time + " and place " + m_place + "!")
								m_sock = get_connection_by_user(m_user)
								if m_sock != None:
									m_sock.send("New Match with " + username + " at time " + time + " and place " + place + "!")
						else:
							sock.send("No Matches yet!\n")
						continue

					if command == "send":
						username = get_user_by_connection(sock)
						user_to_send = data_split[1]
						msg_list = data_split[2:]
						msg = ' '.join(msg_list)
						sock_to_send = get_connection_by_user(user_to_send)
						if sock_to_send != None:
							sock_to_send.send("recv " + username + " " + msg)
						continue

					broadcast(server_socket, sock, "\r" + '[' + str(sock.getpeername()) + '] ' + data)  
				else:
					# remove the socket that's broken    
					if sock in SOCKET_LIST:
						SOCKET_LIST.remove(sock)

					# at this stage, no data means probably the connection has been broken
					broadcast(server_socket, sock, "Client (%s, %s) is offline\n" % addr) 

	server_socket.close()
	
# broadcast chat messages to all connected clients
def broadcast (server_socket, sock, message):
	for socket in SOCKET_LIST:
		# send the message only to peer
		if socket != server_socket and socket != sock :
			try :
				socket.send(message)
			except :
				# broken socket connection
				socket.close()
				# broken socket, remove it
				if socket in SOCKET_LIST:
					SOCKET_LIST.remove(socket)
 
if __name__ == "__main__":

	sys.exit(start_server())
