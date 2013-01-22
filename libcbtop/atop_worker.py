# run atop
# convert that to a python dictionary which can be sent back 
 
#two parser , one that parses system stats , the other one process leve stats
 
import re
 
class AtopParser(object):
 
    @staticmethod
    def convert_to_json(atop_lines):
        # split lines , then read first line splt by space and read the date and time then
        system_lines = []
        proc_lines = []
        # assuming that the output starts with system level stats and
        # then continues with process level stats
        parsing_system = False
        parsing_proc = False
        for line in lines:
            if line.startswith('ATOP -'):
                parsing_system = True
                continue
            if line.find("*** system and process activity since boot ***") >= 0:
                parsing_system = False
                parsing_proc = True
                continue 
            if parsing_system:
                system_lines.append(line)
            if parsing_proc:
                proc_lines.append(line)
        sys_stats = AtopParser.parse_system_stats(system_lines)
        proc_stats = AtopParser.parse_proc_stats(proc_lines)
        return sys_stats + proc_stats
 
    @staticmethod
    def parse_system_stats(data):
      parseables = {}
      parseables.update({'CPU':{'sys':'time-formatted', 'user':'integer', 
                   'irq':'integer', 'idle':'integer', 'wait':'integer'}})
      parseables.update({'cpu':{'sys':'percentage', 'user':'percentage',
                    'irq':'percentage', 'idle':'percentage',
                     'cpu${*}':'percentage'}})
      parseables.update({'MEM':{'tot':'formatted-integer', 'free':'formatted-integer',
                    'cache':'formatted-integer', 'buff':'formatted-integer',
                    'slab':'formatted-integer'}})
      parseables.update({'SWP':{'tot':'formatted-integer', 'free':'formatted-integer',
                    '${*}':'${*}',
                    'vmcom':'formatted-integer', 'vmlimit':'formatted-integer'}})
      parseables.update({'PAG':{'scan':'integer', 'stall':'integer', 'swin':'integer',
                   'swout':'integer'}})
      parseables.update({'LVM':{'${*}':'string', 'busy':'percentage', 'read':'integer',
                    'write':'integer', 'avio':'time-formatted'}})
 
      parseables.update({'DSK':{'${*}':'string', 'busy':'percentage', 'read':'integer',
                    'write':'integer', 'avio':'time-formatted'}})
      all_parsed = []
      #print parseables
      for line in data:
          parsed = {}
          o = AtopParser.organize_sys(line)
          if o[0] in parseables:
              # parse and format
              keyword = o[0]
              parsed['name'] = keyword
              for pair in o[1:]:
                  
                  parsed[pair[0]] = pair[1]
                  # parse pairs[1]
                  schema = parseables[o[0]]
                  if pair[0].lower() in schema:
                      unit = schema[pair[0]]
                      if unit == 'formatted-integer':
                          parsed[pair[0]] = AtopParser.convert_formatted_integer(pair[1])
                      elif unit == 'percentage':
                          parsed[pair[0]] = AtopParser.convert_percentage_integer(pair[1])
              all_parsed.append(parsed)
      return all_parsed
   
 
    @staticmethod
    def organize_proc(line):
        orgainzed = []
        tokens = line.split(' ')
        tokens = filter(lambda x: x is not '', tokens)
        if len(tokens) != 12:
            return {}
        lastIndex = len(tokens) - 1
        parsed = {'process':tokens[lastIndex],
               'PID':tokens[0],'SYSCPU':tokens[1], 'USRCPU':tokens[2], 
                'VGROW':tokens[3], 'RGROW':tokens[4], 'RDDSK':tokens[5],
                'WRDSK':tokens[6], 'ST':tokens[7], 'EXC':tokens[8],
                'S':tokens[9], 'CPU':tokens[10], 'CMD':tokens[11]}
        return parsed
     
    @staticmethod
    def organize_sys(line):
        organized = []
        tokens = line.split(" ")
        tokens = filter(lambda x: x is not '', tokens)
        seq = AtopParser.advance(tokens, 0)
        while seq != -1:
            if len(organized) < 1:
               organized.append(tokens[seq])
            else:
                if AtopParser.advance(tokens, seq + 1) == seq + 1:
                    # for s0 666 Kbps we need two tokens
                    if seq + 2 < len(tokens) and tokens[seq + 2] is not '|':
                        organized.append([tokens[seq], 
                            '%s%s' % (tokens[seq+1],tokens[seq+2])])
                        seq = seq + 2
                    else: 
                        organized.append([tokens[seq], tokens[seq+1]])
                    seq = seq + 1
                else:
                   organized.append([tokens[seq], 'n/a'])
            seq = AtopParser.advance(tokens, seq + 1)
        return organized
 # advance to next
    @staticmethod
    def advance(tokens, index):
        while  index < len(tokens) and ( tokens[index] is '' or tokens[index] is '|' ):
            index = index + 1
        if index >= len(tokens):
            return -1
        return index
 
    @staticmethod
    def parse_line(line, parseables):
        tokens = line.split(" ")
        #print tokens
        converted = {}
        if tokens:
            for p in parseables:
                pname = p.keys()[0]
                if pname == tokens[0]:
                    converted['name'] = pname
                    columns = p[pname]
                    seq = 0
                    for t in tokens[1:]:
                        if not t or t is ' ' or t is '|':
                            continue
                        if t == columns.keys()[seq]:
                            continue
                        seq = seq + 1
                    break    
        return converted
 
    @staticmethod
    def parse_proc_stats(data):
        proc_stats = []
        columns = {'pid':'integer', 'syscpu':'time', 'usrcpu':'time-formatted',
                   'vgrow':'integer-formatted', 'rgrow':'integer-formatted',
                   'rddsk':'integer-formatted','st':'string','s':'string',
                   'cpu':'percentage','cmd':'name'}
        for line in data:
            proc_stat = AtopParser.organize_proc(line)
            if proc_stat:
                proc_stats.append(proc_stat)
        return proc_stats
 
 
    @staticmethod
    def convert_percentage_integer(value):
        perc = value.find('%')
        if perc > 0 :
            return value[0:perc]
        return -1
 
    @staticmethod
    def convert_formatted_integer(value):
        r = re.compile('([1-9][0-9]*)([kKmMbBgG]?)')
        result = r.match(value)
        units={'k':pow(10,3),'m':pow(10,6),'g':pow(10,9),'b':pow(10,12),'u':pow(10,0)}
        if result.group(2) == '':
            unit = 'u'
        else:
            unit = result.group(2).lower()
        return int(result.group(1)) * units[unit]
 
file = open("/Users/chisheng/atop-sample.txt").read()
lines = []
if file:
    lines.extend(file.split('\n'))
parser = AtopParser.convert_to_json(lines)
print parser
