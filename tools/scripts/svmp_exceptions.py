import sys
import traceback

try:
  from pywintypes import com_error
except: pass

class SvmpToolsError(Exception):
    """ Custom error output for Geoprocessing scripts.
        
    Returns formatting error message, GP errors (if they exist)
    and python tracebacks if DEBUG=True.
    
    TODO: generate more or less verbose output based on exception type.
    
    References:
     * http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
     * http://webhelp.esri.com/arcgisdesktop/9.2/index.cfm?TopicName=GetMessages_method
    """    
    
    def __init__(self,gp,
          severity=2,parent_exc=None,full_tb=False,
          pretty_print=True,exit_clean=True,
          debug=False,pdb=False,send_mail=False):
        """Create an instance of an error.
        """
        
        # Optional keyword arguments 
        self.gp = gp
        self.debug = debug
        self.pdb = pdb
        self.exit_clean = exit_clean
        self.full_tb = full_tb
        self.severity = severity
        self.parent_exc = parent_exc
        self.pretty_print = pretty_print
        self.send_mail = send_mail
        
        # Parameters to populate
        self.message = 'An unknown error occured'
        self.python_error = None
        self.arc_error = None

    def __str__(self):
        return repr(self.message)
        
    def set_trace(self):
        """
        Routine to set a Python Debugger trace.
        
        http://www.ferg.org/papers/debugging_in_python.html
        """
        try:
          print ">>> Entering PDB interpreter (press 'c' to leave)"
          import pdb
          pdb.set_trace()
        except KeyboardInterrupt:
          pass
 
    def pretty_msg(self):
        """Pretty print an error message in an ascii box.
        """
        lines = self.message.splitlines()
        max_len = 0
        msg_line = ''
        for line in lines:
          if len(line)> max_len:
            max_len = len(line)
          msg_line += '\n| %s |\n' % line
        
        msg = '\n|%s--|' % (max_len*'-')
        msg += msg_line
        msg += '|%s--|\n' % (max_len*'-')
        return msg

    def get_traceback(self):
        python_error = ''
        exc_class, exc, tb = sys.exc_info()
        try:
          if isinstance(exc,com_error):
            commsg = exc[2][2]
            if commsg:
               self.message = commsg
               self.arc_error = "COM error:\nType:'%s'\n%s\n" % (exc[0],commsg)
        except: pass
        tbinfo = traceback.format_tb(tb)
        if tbinfo:
            if self.full_tb:
              tb_msg = '\n'.join(tbinfo[:])
            else:
              tb_msg = tbinfo[0]
            python_error = 'Python Error:\nTraceback:\n%s\nInfo:\n\t%s: %s\n' % (tb_msg,exc_class,exc)
            self.python_error = python_error

    def get_arc_messages(self):
        arc_error = ''
        msgs = self.gp.GetMessages(self.severity)
        if msgs:
          arc_error = 'Geoprocessing Error:\n%s\n' % msgs
          self.arc_error = arc_error
    
    def mail_errors(self,USE_GMAIL=True):
        try:
          import smtplib
          from email.mime.text import MIMEText
          self.debug = True
          self.pdb = False
          self.full_tb = True
          self.severity = 0
          self.pretty_print = False
          error_text = self.get_arc_messages()
          error_text += self.get_traceback()        
          msg = MIMEText(error_text)
          msg['Subject'] = 'SVMP TOOLS ERROR'
          msg['From'] = 'dbsgeo@gmail.com'
          msg['To'] = 'dbsgeo@gmail.com'
          s = smtplib.SMTP()
          s.set_debuglevel(0)
          if USE_GMAIL:
            s.connect('smtp.gmail.com', 587)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login('dane.mapnik@gmail.com', '.osmapnik')
          else:
            s.connect(host='localhost',port=587)
          # sendmail(self, from_addr, to_addrs, msg, mail_options=[], rcpt_options=[])
          s.sendmail(msg['From'], [msg['To']], msg.as_string())
          s.close()
        except:
          pass
                
    def return_errors(self):
        """Return exception message and any geoprocessing and python errors.
        
        """
        # Build up errors if they exist
        # For gp...
        self.get_arc_messages()
        # For python...
        self.get_traceback()
        
        if self.pretty_print:
          msg = self.pretty_msg()
        else:
          msg = self.message
        
        if self.arc_error:
          self.gp.AddError(msg)
          self.gp.AddError(self.arc_error)
        else:
          self.gp.AddError(msg)
        
        if self.debug:
          if self.python_error:
            self.gp.AddError(self.python_error)
          
    def cleanup(self):
        if self.exit_clean:
          # Delete the gp library import otherwise
          # this process may continue running independent
          # of the script process.
          #del self.gp
          # this call is needed to exit the script when
          # run from the cmd line
          sys.exit(1)
          # This raise seems to be the cleanest way to halt the script
          # when run from the Toolbox Dialog, but may not be ideal because
          # it means you will only see the 'last' error, which could be a red
          # herring
          
          # There may be a better final Exception type to raise to end the script
          # cleanly when run from the toolbox
          raise SystemExit
        else:
          # will recursively tumble through errors
          pass

    def call(self,message=''):
        if message:
          if isinstance(message,Exception):
            try:
              self.message = message.message
            except:
              pass
          else:
            self.message = message
        # Call function to return errors to screen
        self.return_errors()
        if self.pdb:
          self.set_trace()
        if self.send_mail:
          self.mail_errors()
        self.cleanup()