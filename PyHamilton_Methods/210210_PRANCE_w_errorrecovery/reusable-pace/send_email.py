import smtplib
from time import sleep
from email.message import EmailMessage

num_py_proc=0
class notify_by_mail:
    def __init__ (self,errorMsg):
        mail_user = 'starlet@btumail.org'
        mail_password = 'starlet'
        self.msg = EmailMessage()
        self.msg['Subject']= 'HAM SMASH'
        self.msg['From']   = mail_user 
        self.msg['To']   =  'starlet@btumail.org'
        self.msg.set_content(errorMsg)
        
        
        self.server = smtplib.SMTP('btumail.org', 587)
        self.server.ehlo()
        self.server.starttls()
        self.server.ehlo()
        self.server.login(mail_user, mail_password)
        
    def send_msg (self,address):
        self.msg.replace_header('To',address)
        self.server.send_message(self.msg)

    

#print("python.exe" in (p.name() for p in psutil.process_iter()))
if __name__ == '__main__':
    import psutil
    for p in psutil.process_iter():
        if p.name()=='py.exe':
            num_py_proc+=1
    print(num_py_proc)
    while True:
        cur_num=0
        try:
            for p in psutil.process_iter():
                if p.name()=='py.exe':
                    cur_num+=1
        except:
            continue
        if cur_num<num_py_proc:
            print('crashed!!!')
            notifier=notify_by_mail('ham smash')
            notifier.send_msg('tutu8888@gmail.com')
            print('email sent')
            break
        else:
            print('ok')
            sleep(30)


#notify_BT_by_mail()