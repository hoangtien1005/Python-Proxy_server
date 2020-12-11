
import socket
import sys
import _thread
import traceback
import http.server
import socketserver
import os
import time
import errno

BUFFER_SIZE = 999999                        # kích thước data tối đa
MAX_CONN = 100                              # số connection tối đa
LISTEN_PORT = 8888                          # port lắng nghe
BLACKLIST_FILE_PATH ="blacklist.conf"       # đường dẫn file blacklist
HTML_FILE_PATH ="403.html"                  # đường dẫn file html


def main():
    black_list = read_File()                 # danh sách domain cấm
   
    
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # khởi tạo socket 
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # tái sử dụng socket
        s.bind(("", LISTEN_PORT))                               # bind port và address ( ở đây là local host)
        s.listen(MAX_CONN)                                      # lắng nghe
        
        print("[*] KHỞI TẠO THÀNH CÔNG: [{}]".format(LISTEN_PORT))

    except Exception as e:
        #print(e)
        sys.exit(2)

    while 1:
        try:
            conn,addr = s.accept()                              # accept kết nối từ browser
            _thread.start_new_thread(Request_Handle,(conn,addr,black_list)) # tạo thread xử lý

        except:
            pass

def Request_Handle(conn, addr,black_list):                      #hàm xử lý request

    try: 
        request = conn.recv(BUFFER_SIZE)
        print(request)                        #nhận request
        first_line = request.decode("utf-8").split("\n")[0]
        print(first_line)                                       # in request sau khi decode
        url = first_line.split(" ")[1]
        for domain in black_list:                               # tìm xem domain trong blacklist có nằm trong url không                            
            if domain in url:           
                print("BLOCKED ",url)
                response = request_forbidden()                  # trả về status_code 403 và hiển thị html
                conn.sendall(response)
                conn.close()

        http_pos = url.find("://")
        if http_pos == -1:
            temp = url
        else:
            temp = url[(http_pos + 3):]
 
        port_pos = temp.find(":")           # tìm port của web server ( nếu có )
        webserver_pos = temp.find("/")      # tìm vị trí cuối cùng của chuỗi web server
        if webserver_pos == -1:
            webserver_pos = len(temp)
        webserver = ""
        port = -1
        if port_pos == -1 or webserver_pos < port_pos:          # port mặc định
            port = 80                       
            webserver = temp[:webserver_pos]
        else:
            port = int(temp[(port_pos + 1):][:webserver_pos - port_pos -1])
            webserver = temp[:port_pos]
 
        print("WEB SERVER: ",webserver)

        proxy_server(webserver,port,conn,request,addr)      # gửi request lên web server
        
    except Exception as e:
        #print(e) 
        #traceback.print_exc()
        pass

def read_File():                            #đọc từ file blacklist.conf
    f = open(BLACKLIST_FILE_PATH)
    temp = f.readlines()
    black_list = list()
    for i in temp:
        black_list.append(i[:len(i)-1])   #thêm từng dòng vào list 
    f.close()
    return black_list                     # trả về list



def request_forbidden():                 #trả về 403 response
    f=open(HTML_FILE_PATH)
    html_data = f.read()                 # đọc từ file 403.html rồi lưu vào data
    f.close()

    data=""
    data+="HTTP/1.1 403 Forbidden\r\n"
    time_now = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    data += "Date: {}\r\n".format(time_now)
    data+="Content-type: text/html; charset=utf-8\r\n"
    data+="\r\n"                                            # thêm các header
    data+=html_data                                         
    data+="\r\n\r\n"
    encode_data = data.encode()                             # trả về sau khi encode
    return encode_data


def proxy_server(webserver, port, conn, request, addr):    #gửi request lên server và nhận data để gửi lại browser
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #tạo socket để kết nối tới web server
        s.connect((webserver, port))
        s.send(request)                                         #gửi request lên web server
        while 1:
            reply = s.recv(BUFFER_SIZE)                         #nhận response từ web server
            
            if len(reply) > 0:
                conn.sendall(reply)                             #gửi response về web browser
                print("[*] Request gửi thành công: {} , {}".format(addr[0],webserver))
            else:
                break  

        s.close()
        conn.close()

    except socket.error as error:
        (value, message) =error.args    #có thể là do chứa https request
        print(value,message)
        if s:
            s.close()
        if conn:
            conn.close()
        sys.exit(1)

main()