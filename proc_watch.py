#!/usr/bin/env python

# rewrite of cpu monitor script in python
# edit config_file and smtplib.SMTP var to match the location to you ini file, and your smtp server
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import pickle
import pwd
import signal
import smtplib
import socket
import subprocess
import sys
import time
import ConfigParser
from email.mime.text import MIMEText
from string import Template

# location of config file
#config_file = "/usr/local/etc/proc_watch.ini"
config_file = "./proc_watch.ini"

# read in the config file
configParser = ConfigParser.RawConfigParser()
configParser.read(config_file)

# define some variables here
ps_cmd          = 'ps -e -o pid,uid,%cpu,%mem,args'  # ps command
user_uid_min    = configParser.getint("limits", "user_uid_min") # only watch uids in this range
user_uid_max    = configParser.getint("limits", "user_uid_max")
max_cpu         = configParser.getfloat("limits", "max_cpu") # cpu limits
max_mem         = configParser.getfloat("limits", "max_mem") # memory limits

run_dir     = configParser.get("paths", "run_dir")
log_dir     = configParser.get("paths", "log_dir")
histfile    = run_dir+"/proc_watch.history"     # track multiple violations
logfile     = log_dir+"/proc_watch.log"         # actions logged to this file

exclude_comms = tuple(configParser.get("limits","commands").split(","))

def send_email(name, account, hostname, date, command, pid, mem, cpu):
  mail_from = configParser.get("mail", "from")
  mail_reply_to = configParser.get("mail", "reply_to")
  mail_smtp = configParser.get("mail", "smtp_server")
  mail_to   = account

  config_msg  = configParser.get("mail", "message")
  config_sub  = configParser.get("mail", "subject")
 
  msg_template = Template(config_msg)
  sub_template = Template(config_sub)
  mail_message = msg_template.substitute(account=account, command=command, cpu=cpu, date=date, hostname=hostname, mem=mem, name=name, pid=pid, n=" ")
  mail_subject = sub_template.substitute(account=account, hostname=hostname, name=name, date=date)
  
  mime_message  = MIMEText(mail_message)
  mime_message['Subject']    = mail_subject
  mime_message['From']       = mail_from
  mime_message['To']         = mail_to
  mime_message['Reply-to']   = mail_reply_to

  s = smtplib.SMTP(mail_smtp)
  s.sendmail(mail_from, mail_to, mime_message.as_string())
  s.quit()

def log_proc(l_proc,action):
  pid,uid,cpu,mem,command  = tuple(l_proc)
  account   = pwd.getpwuid(uid).pw_name
  hostname  = socket.gethostname()
  date      = time.strftime('%Y-%m-%d %H:%M')
  log_fh    = open(logfile, 'a')
  if action == "ignore":
    log_fh.write("%s - Ignoring pid: %s. user: %s, host: %s, cpu: %s, mem: %s, comm: %s\n" % (date, pid, account, hostname, cpu, mem, command))
  elif action == "term":
    log_fh.write("%s - Sending SIGTERM to pid: %s. user: %s, host: %s, cpu: %s, mem: %s, comm: %s\n" % (date, pid, account, hostname, cpu, mem, command))
  elif action == "kill":
      log_fh.write("%s - Sending SIGKILL to pid: %s. user: %s, host: %s, cpu: %s, mem: %s, comm: %s\n" % (date, pid, account, hostname, cpu, mem, command))
  log_fh.close()

def kill_proc(l_proc):
  pid,uid,cpu,mem,command  = tuple(l_proc)
  u         = pwd.getpwuid(uid)
  name      = u.pw_gecos
#  name      = "%s %s" % (u.pw_gecos.split(",")[1],u.pw_gecos.split(",")[0])
  account   = u.pw_name
  hostname  = socket.gethostname()
  date      = time.strftime('%Y-%m-%d %H:%M')
  try:
    os.kill(int(pid), 0)
    log_proc(l_proc,"term")
    os.kill(int(pid), signal.SIGTERM) 
    send_email(name, account, hostname, date, command, pid, mem, cpu)
    time.sleep(2)
  except:
    pass
  try:
    os.kill(int(pid), 0)
    log_proc(l_proc,"kill")
    os.kill(int(pid), signal.SIGKILL)
  except:
    pass


def gen_procs():
  d_ps,d_ignore = {}, {}
  p = subprocess.Popen(ps_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  psout, pserr = p.communicate()
  ps_lines   = [ line for line in psout.split('\n') if line ]
  for line in ps_lines[1:]:
    proc = line.split() 
    pid  = int(proc[0])
    uid  = int(proc[1])
    cpu  = float(proc[2])
    mem  = float(proc[3])
    if ( uid >= user_uid_min and uid < user_uid_max ) and ( cpu >= max_cpu or mem >= max_mem ):
      command = str(" ".join(proc[4:]))
      del proc[5:]
      d_ps[pid] = [pid,uid,cpu,mem,command]
  return d_ps

def write_history(proc_dict,file_path):
  hist_fh      = open(file_path, 'wb')
  pickle.dump(proc_dict, hist_fh)
  hist_fh.close()

def read_history(file_path):
  hist_fh      = open(file_path, 'rb')
  proc_dict = pickle.load(hist_fh)
  hist_fh.close()
  return proc_dict

def run_procs(d_hist, d_curr):
  for pid in d_curr.keys():
    command = d_curr[pid][4]
    if command.startswith(exclude_comms):
      pid_ignore = True
    else:
      pid_ignore = False 
    if pid_ignore and pid not in d_hist.keys():
      d_hist[pid] = d_curr[pid]
      log_proc(d_curr[pid],"ignore")
    elif pid_ignore and pid in d_hist.keys():
      d_hist[pid] = d_curr[pid]
    elif not pid_ignore and pid not in d_hist.keys():
      d_hist[pid] = d_curr[pid]
    elif not pid_ignore and pid in d_hist.keys():
      kill_proc(d_curr[pid])
      d_hist[pid] = d_curr[pid]
  for pid in d_hist.keys():
    if pid not in d_curr.keys():
      del d_hist[pid]
  write_history(d_hist,histfile)

if not os.path.exists(run_dir):
  os.makedirs(run_dir)

if os.path.isfile(histfile):
  firstrun = False
else:
  firstrun = True

process_dict = gen_procs()

if firstrun:
  write_history(process_dict,histfile)
  exit(0)
if not firstrun:
  hist_dict = read_history(histfile)
  run_procs(hist_dict, process_dict)
 
