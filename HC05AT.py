# Python, Frank’s HC-05 communication program
import serial
import time
import sys
import signal
import re

import threading
import queue

OKtext = re.compile("OK")
ERRtext = re.compile("ERROR")

def signal_handler(signal, frame):
    print("closing program by SIGINT")
    if ( type(SerialPort).__name__ == 'Serial'):
        SerialPort.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# shortcut to use unformatted write routine instead of 'print'
surpress_output = False
def prnt(s):
    if ( not surpress_output ):
        sys.stdout.write(s)
        sys.stdout.flush()

input_queue = queue.Queue()
stop_has_been_signaled = False
saved_address_setting = ""

SerialPort = ""
def connect_serial_port():
    global SerialPort
    COM = "COM15"
    BAUD = 9600

    #COM=input("Enter the COM Port\n")
    #BAUD=input("Enter the Baudrate\n")

    while (1):
        try:
            SerialPort = serial.Serial(COM,BAUD,timeout=1.0)
            break
        except KeyboardInterrupt:
            prnt("Exiting the program")
            #SerialPort.close()
            sys.exit(0)
        except:
            prnt(".")
            time.sleep(2)
 

############# KEYBOARD INPUT  #############################################################

def console_input_thread(input_queue): #runs in thread context so pass it input queue
    import msvcrt
    global stop_has_been_signaled
    if sys.stdin.isatty():
        prnt( '| stdin IS a tty, accepting input\n')
        try:

            while not stop_has_been_signaled:
                thechar = msvcrt.getch()
                if thechar.isalnum():
                    input_queue.put(thechar)
                time.sleep(.05)
        except:
            prnt("Closing and exiting the program")
            stop_has_been_signaled = True
    else:
        prnt('| stdin IS NOT a tty, ')
    prnt( 'Exiting input thread' )

def check_console():
    global stop_has_been_signaled
    if not stop_has_been_signaled:
        inputed = ''
        if not input_queue.empty():
            inputed = input_queue.get()
        return inputed



############  MODULE  #################################################    
cmdstrings = ["","+ROLE","+ADDR","+BIND","+CMODE","+UART","+NAME","+PSWD"]
module_settings = ["","","","","","","",""] # place to store retrieved config values
data_str = ""    #store incoming chars for processing

def process_module_output():   # all incoming responses processed here
    global SerialPort
    global data_str
    while ( not SerialPort.isOpen() ):
        time.sleep(2.0)
        connect_serial_port()

    while(1):
        try:
            waiting = SerialPort.inWaiting()
            if (waiting>0):   # append all incoming characters
                data_str += SerialPort.read(waiting).decode("utf-8")
                #print(data_str,end="")
            else:
                break
        except Exception as e:
            print(type(e))
            print(e)
            SerialPort.close()
            sys.exit(0)

        while(1):      # process all complete lines
            linelength = data_str.find('\n')
            if(linelength < 0):
                break
            IncomingData = data_str[:linelength+1] #copy only one line
            data_str = data_str[linelength+1:]     # and remove it from incoming stream
            if (OKtext.search(str(IncomingData))):   # process special lines OK ad ERR
                prnt("  >> OK\n")
            elif (ERRtext.search(str(IncomingData))):
                prnt(">> ERR: "+str(IncomingData)+"\n")
                #SerialPort.write(bytes("AT\r",'utf-8'))
            else:
                prnt(IncomingData[:-2])  #Show the line without \r\n at the end
                cmdstart = IncomingData.find('+')
                if ( cmdstart >= 0):   # if there is a +, it is a response to a sent command
                    index = 0
                    for i in range(1,len(cmdstrings)):
                        #if ( IncomingData[cmdstart+1:cmdstart+5].find(cmdstrings[i][1:5]) > 0 ):
                        if ( IncomingData.find(cmdstrings[i][1:4]) > 0 ):
                             index = i
                             break
                        if ( IncomingData.find("PIN") > 0):
                            index = 7
                            break
                    if ( index == 0 ):    # no command found, no further processing
                        prnt (" > ")
                    else:
                        if (index == 1):  #convert role
                            if (str(IncomingData[6]) == '0'):
                                module_settings[1] = "SLAVE "
                            else:
                                if (str(IncomingData[6]) == '1'):
                                    module_settings[1] = "MASTER"
                                else:
                                    module_settings[1] = "WRONG"
                        elif (index == 4):
                            if (str(IncomingData[5]) == ':'):
                                tmpcmode = str(IncomingData[6])
                                cmdstrings[4] = "+CMOD:"
                            else:
                                tmpcmode = str(IncomingData[7])
                            if ( tmpcmode == '0' ):
                                module_settings[4] = "MONO "
                            else:
                                module_settings[4] = "WRONG"
                        elif (index == 7):
                            if (str(IncomingData[4]) == ':'):
                                tmpcmode = str(IncomingData[5:-2])
                            else:
                                tmpcmode = str(IncomingData[6:-2])
                            module_settings[7] = tmpcmode
                        else:
                            module_settings[index] = str(IncomingData[6:-2])
                else:
                    if (    IncomingData.find("TX") >= 0
                         or IncomingData.find("VERS") >= 0):
                        prnt( " > ")    # these are expected lines, just continue
                    else:
                        prnt( " \'+\' NOT FOUND ") #otherwise not expected

## OUTPUT send commands functions
def send_cmd_to_hc05_module(cmdindex):
            try:
                OutgoingData='AT'+str(cmdstrings[cmdindex])+"\r\n"
                prnt(">AT"+str(cmdstrings[cmdindex])+" >> ")
                SerialPort.write(bytes(OutgoingData,'utf-8'))
                time.sleep(.3)
            except KeyboardInterrupt:
                prnt("ControlC seen in send. ")
                stop_has_been_signaled = True
                time.sleep(1)
                SerialPort.close()
                sys.exit(0)
            except Exception as e:
                print(type(e))
    
#output a line to show all stored values
def show_settings():
    global saved_address_setting
    prnt("SETTINGS:\n")
    prnt(str(cmdstrings[1][1:])+"="+module_settings[1]+" ")
    if ( module_settings[1] == "SLAVE " ):
        prnt(str(cmdstrings[3][1:])+"="+module_settings[3]+" ") #reverse addresses for slave
        prnt(str(cmdstrings[2][1:])+"="+module_settings[2]+" ")
    else:
        prnt(str(cmdstrings[2][1:])+"="+module_settings[2]+" ")
        prnt(str(cmdstrings[3][1:])+"="+module_settings[3]+" ")
    for i in range(4,7):
        prnt(str(cmdstrings[i][1:])+"="+module_settings[i]+" ")
    if ( len(module_settings[7]) > 0 ):
        if ( module_settings[7][0] == "\"" ):
            prnt("PIN:="+module_settings[7]+" ")
        else:
            prnt("PSWD="+module_settings[7]+" ")
        
    prnt("saved="+saved_address_setting)
    prnt("\n")

########################################################################
##### THESE ROUTINES ARE CALLED BY KEY COMMANDS, SEE HELP ##############
def update_settings():
   # time.sleep(.8)
    for ix in range(1,len(cmdstrings)):
        process_module_output()
        send_cmd_to_hc05_module(ix)
    time.sleep(.5)
    process_module_output()
    show_settings()

#    ←[48;5;22m    ←[49m0:
def showhelp():
    prnt("*********  Key Commands: h - this help  **************\n")
    prnt("R remember ADDR to saved address, I install saved address to BIND, E enter new BIND address\n")
    prnt("C config base parameters, M set master, S set slave, U update display, q - quit, s - show current\n")
    for i in range(0,len(cmdstrings)):
        prnt(str(i)+": AT"+str(cmdstrings[i])+"  ")
    prnt("\n******************************************************\n")
    time.sleep(.2)

# to set a custom name
def setname():
    input_thread.paused = True
    newname = input("NEWNAME?")
    SerialPort.write(bytes("AT+NAME="+newname+"\r\n",'utf-8'))
    module_settings[6] = newname
    SerialPort.write(bytes("AT+NAME\r\n",'utf-8'))
    input_thread.paused = False
                    
def save_this_address():
    global saved_address_setting
    if ( len( module_settings[2]) > 0 ):
        with open("savedaddressfile.txt",'w') as addfile:
            addfile.write(module_settings[2])
        saved_address_setting = module_settings[2]
        prnt("Remembered address"+saved_address_setting.replace(':',',')+"\n")

def use_saved_address():
    global saved_address_setting
    module_settings[3] = saved_address_setting
    SerialPort.write(bytes("AT+BIND="+saved_address_setting.replace(':',',')+"\r\n",'utf-8'))

def enter_bind_address():
    input_thread.paused = True
    newbind = input("NEWBIND?")
    SerialPort.write(bytes("AT+BIND="+newbind.replace(':',',')+"\r\n",'utf-8'))
    input_thread.paused = False
    time.sleep(.5)
    update_settings()
    
def config_base_settings():
    SerialPort.write(bytes("AT+UART=9600,0,0\r\n",'utf-8'))
    prnt("AT+UART=9600,0,0 ")
    time.sleep(.2)
    process_module_output()
    SerialPort.write(bytes("AT+CMODE=0\r\n",'utf-8'))
    prnt("AT+CMODE=0 ")
    time.sleep(.2)
    process_module_output()
    SerialPort.write(bytes("AT+PSWD=\"3412\"\r\n",'utf-8'))
    prnt("AT+PSWD=\"3412\" ")
    process_module_output()
    time.sleep(.2)
    SerialPort.write(bytes("AT+NAME=SPARKY\r\n",'utf-8'))
    prnt("AT+NAME=SPARKY ")
    process_module_output()
    time.sleep(.2)
    SerialPort.write(bytes("AT+CMODE=0\r\n",'utf-8'))
    prnt("AT+CMODE=MONO ")
    time.sleep(.2)
    process_module_output()
    update_settings()

############  MAIN  #################################################    

connect_serial_port()        
        
time.sleep(.2)

#  START THE CONSOLE INPUT THREAD
input_thread = threading.Thread(target=console_input_thread, args=(input_queue,))
input_thread.daemon = True
input_thread.start()
time.sleep(2.2)

# READ THE SAVED ADDRESS IF PRESENT
try:
    with open("savedaddressfile.txt",'r') as addfile:
        saved_address_setting = addfile.read()
except IOError:
    pass

## STARTUP PREPARATION    
process_module_output()
showhelp()
update_settings()

#  PROCESS All CONSOLE COMMANDS
while (1):
    inchar = check_console()
    if inchar:
        if ( inchar.isdigit() ):
            incharint = int(inchar)
        else:
            incharint = -1 
        if (inchar == b'h'):
            showhelp()
        elif (inchar == b'q'):
            break
        elif (  (incharint >= 0) and (incharint < len(cmdstrings))):
            try:
                OutgoingData='AT'+str(cmdstrings[incharint])+"\r\n"
                prnt("\rAT"+str(cmdstrings[int(inchar)])+" >> ")
                #SerialPort.reset_input_buffer()
                SerialPort.write(bytes(OutgoingData,'utf-8'))
                time.sleep(.03)
            except KeyboardInterrupt:
                prnt("ControlC Closing and exiting the program")
                stop_has_been_signaled = True
                time.sleep(1)
                SerialPort.close()
                sys.exit(0)
        elif (inchar == b's'):
            show_settings()
        elif (inchar == b'Y'):
            setname()
        elif (inchar == b'S'):   # Set to 'S'lave mode
            surpress_output = True
            process_module_output()
            SerialPort.write(bytes("AT+ROLE=0\r\n",'utf-8'))
            time.sleep(.2)
            process_module_output()
            SerialPort.write(bytes("AT+ROLE\r\n",'utf-8'))
            time.sleep(.1)
            process_module_output()
            surpress_output = False
            show_settings()
        elif (inchar == b'M'):   # set to 'M'aster
            surpress_output = True
            process_module_output()
            SerialPort.write(bytes("AT+ROLE=1\r\n",'utf-8'))
            time.sleep(.2)
            process_module_output()
            SerialPort.write(bytes("AT+ROLE\r\n",'utf-8'))
            time.sleep(.1)
            process_module_output()
            surpress_output = False
            show_settings()
        elif (inchar == b'U'):  # 'U'pdate read all settings from module
            update_settings()
        elif (inchar == b'R'):  # save this module's ADDR   'COPY'
            save_this_address()
        elif (inchar == b'I'):  # 'I'nstall saved ADDR to this modules BIND address
            use_saved_address()
        elif (inchar == b'E'):  # 'E'nter type in a custom BIND value
            enter_bind_address()
        elif (inchar == b'C'):  # 'C'onfigure module with standard Sparky values
            config_base_settings()
        elif (inchar == b'F'):  # 'F'actory reset settings
            SerialPort.write(bytes("AT+ORGL\r\n",'utf-8'))
            time.sleep(.5)
            update_settings()
        elif (inchar == b'V'):  # show 'V'ersion string
            SerialPort.write(bytes("AT+VERSION\r\n",'utf-8'))
        else:  
            prnt("UNREC"+str(inchar)+hex(ord(inchar))+":\n") #unrecognized command char
    process_module_output()       
# end of while loop
            
prnt("Escaping and exiting the program")
stop_has_been_signaled = True
time.sleep(1)
SerialPort.close()
sys.exit(0)

    
