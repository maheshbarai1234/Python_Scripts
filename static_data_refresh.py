#!/usr/bin/python

libs = '/nas/prodopsenv/packages/python/modules/mechanize-0.2.5'
import sys
import base64
import re
import getpass
import time
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, libs)
resource = '/export/home/xasvc01/prodopsweb/scripts/libs'
sys.path.insert(0, resource)
import mechanize
from html_render import RenderHTML


class data_refresh:

	def __init__(self):
		self.userid=raw_input("Enter NTID: ")
		self.passwd=getpass.getpass("Enter Password: ").strip()
		self.br = mechanize.Browser()
		self.br.addheaders.append(('Authorization', 'Basic %s' % base64.b64encode('%s:%s' % (self.userid,self.passwd ))))
		self.message='Data Refresh script initiated by user: '+self.userid + '\n\n'
		self.flag =0
		self.server_error = {}
		self.error_log = "Below are Servers with unsuccessful refresh: \n\n"
	def read_properties(self):
		content = open("properties.cfg", 'r').read()
		content = re.sub(r'\n#.+','',content)

		searchObj = re.search( r'env_type="(.+?)"', content, re.I)
		self.env_type = searchObj.group(1).replace("\n","")

		searchObj = re.search( r'envs="(.+?)"', content, re.I)
		envs = searchObj.group(1).replace("\n","")
		
		searchObj = re.search( r'servers="(.+?)"', content, re.I)
		servers = searchObj.group(1).replace("\n","")
		
		searchObj = re.search( r'app_name="(.+?)"', content, re.I)
		app_name = searchObj.group(1).replace("\n","")

		searchObj = re.search( r'static_data_name="(.+?)"', content, re.I)
		self.static_data_name = searchObj.group(1).replace("\n","")

		self.envs = envs.split(',')
		self.servers = servers.split(',')
		self.env_type = self.env_type.lower()
		self.apps = app_name.split(',')
		
		self_html_loc='/apps/home/xasvc01/prodopsweb/html/reports/Alliance/'+self.env_type+'/WAS8/Static_Data_Refresh.html'
		self.html = RenderHTML(self_html_loc)
		self.html.head("Static Data Refresh", 'U8', self_html_loc)
		self.html.tableStart("Static Data Refresh")
		self.html.tableHeaders(["ENV", "SERVER", "APPLICATION" , "STATIC DATA NAME ", "STATUS", "STATUS INFORMATION"])

	def get_supportutils(self):
		sr =  mechanize.Browser()
		sup_url = "http://sesmsupportutilities.allstate.com/reports/Alliance/"+self.env_type+"/WAS8/URLs_Suputils.txt"
		response = sr.open(sup_url)
		content = response.read()
		arr = content.split('\n')
		for items in arr:
			if items =='' : continue
			item_arr = items.split('::')
			env = item_arr[0];server=item_arr[3];url=item_arr[4]
			if (env in self.envs or self.envs[0] == 'ALL') :
				for servers in self.servers:
					if re.search(servers,server,re.I) or servers == 'ALL': 
						for self.app_name in self.apps:
							url = re.sub(r'(http:\/\/.+?\/).+',r'\1',url)
							self.perform_action(env,server,url)
		self.html.tableEnd()
		self.html.foot()
		self.output_file = 'logs/Output.log_'+str(int(time.time()))+'.txt'
		fw=open(self.output_file,'w')
		fw.write(self.message)	
		fw.close()

		#Error_log
		if self.flag == 1:
			self.error_file='logs/Error_log_'+str(int(time.time()))+'.txt'
			fw=open(self.error_file,'w')
	                fw.write(self.error_log)
        	        fw.close()

	def validate_static_data(self,url) :
		try:
			static_url = url + self.app_name +  '/StaticDataUtil.jsp'
			response = self.br.open(static_url)
                        content = response.read()
			if re.search(r'>ISOFireDistrictLookup<',content,re.S):
				return True
			else :
				return False
		except Exception as e :
			return True
	def perform_action(self,env,server,url) : 
		try:
				
			self.message += 'Refreshing Static for SERVER :' + server + ' :: App: '+self.app_name+'\n'
			print 'Refreshing Static for SERVER :' + server + ' :: App: '+self.app_name
			if not self.validate_static_data(url) :
				status = self.static_data_name + " Static data not present"
				print status+ "\n"
				info =  "<b style='color:blue'>"+status+"</b><br />"
				html_info=[env,server,self.app_name,self.static_data_name,info,info]
        	                self.html.tableBody(html_info)
				self.message += status+ '\n'
	                        self.message += '\n\n'
				return	
				
			
			url += self.app_name + '/StaticDataUtil.jsp?cmd=xRx&st=CS&sk='+self.static_data_name
			response = self.br.open(url)
			content = response.read()
			content_grp = re.search(r'name="cmd".+?<td>(.+?)<\/td>',content,re.S)
			output = content_grp.group(1)
			if re.search(r'Successful refresh for static data',output,re.I):
				status =  "<b style='color:green'>Refresh successfully</b><br />"
				info = "<b style='color:green'>"+output+"</b><br />"
				static_data_grp = re.search(r'static\s*data\s+(.+)',output,re.I)
				static_data=static_data_grp.group(1)
			else:
				status =  "<b style='color:blue'>Refresh was Unsuccessful </b><br />"
				info = ''
				static_data = self.static_data_name
			
			app_name_grp = re.search('>Application:<.+?class="normal">(.+?)<',content,re.S)
			app_name = app_name_grp.group(1)
			server_name_grp = re.search('>Server:<.+?class="normal">(.+?)<',content,re.S)
			server_name = server_name_grp.group(1)
			server_name = re.sub(r'(.+?\/.+?)\/.+',r'\1',server_name)
			html_info=[env,server_name,app_name,static_data,status,info]
			self.message += 'Env: ' +env+ '\n' + 'Server: '+server_name+'\n'+'App: '+app_name+'\n'+'Static Result: '+output
			print 'Result: '+output 
			self.html.tableBody(html_info)
			self.message += '\n\n'
			print "\n"
		
		except Exception as e:
			self.message += str(e)+ '\n'
			self.message += '\n\n'
			print str(e)
			print "\n"
			self.error_log += "Server: "+server+"\n"
			self.error_log +="Response: "+str(e)
			self.error_log +="\n\n"
			self.flag =1
			info = re.sub(r'<|>','',str(e))
			status = "<b style='color:red'>Refresh was Unsuccessful </b><br />"
			info =  "<b style='color:red'>"+info+"</b><br />"
			self.server_error[server] = info
			html_info=[env,server,self.app_name,self.static_data_name,status,info]
			self.html.tableBody(html_info)

	#Send email
        def sendemail(self):
		message="The script was executed with below parameter<br />Env Type: "+self.env_type+"<br />Envs: "+str(self.envs)+"<br />Servers: "+str(self.servers)+"<br />Application: "+str(self.apps)+"<br />Static Data Name: "+self.static_data_name+"<br /><br />"
		output_link="http://sesmsupportutilities.allstate.com/reports/Alliance/"+self.env_type+"/WAS8/Static_Data_Refresh.html"
		message += "<b>Output HTML Link:</b> " + output_link + "<br /><br /><br />"
                today = datetime.today()
                email_from = '**********@****.com'
                email_to = "********@********.com"
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "Static data Script Initiated by: " + str(self.userid) + " on " + str(today)
                msg['From'] = email_from
                msg['To'] = email_to

		
		f = file(self.output_file)
		attachment = MIMEText(f.read())
		attachment.add_header('Content-Disposition', 'attachment', filename=self.output_file)           
		msg.attach(attachment)
		message += "<br /><br /><b>************Validating Results*****************</b><br />"
		if self.flag == 1:
			message += "<br /> <b>Validation Failed for below servers</b><br />"
			for items in self.server_error :
				message +='Servers: '+items+' :: Error: '+self.server_error[items] + '<br />'
			 
			f = file(self.error_file)
			attachment = MIMEText(f.read())
			attachment.add_header('Content-Disposition', 'attachment', filename=self.error_file)
			msg.attach(attachment)
		else :
			 message += "<br /> <b>Validation was Success</b><br />"
		message += "<br /><br /><b>Note: </b>Attached is the log file"
	
		html = """\
                <html>
                  <head></head>
                  <body>
                    <p> """ + message + """</p>
                  </body>
                </html>
                """
                mime_type = MIMEText(html, 'html')
                msg.attach(mime_type)

		server = smtplib.SMTP('mail.allstate.com')
                server.sendmail(email_from, email_to, msg.as_string())
                server.quit()

obj = data_refresh()
obj.read_properties()
obj.get_supportutils()
obj.sendemail()
print "Completed Refreshing "+obj.static_data_name+" for mentioned servers\nCheck emails for further details!!!"
