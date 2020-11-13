#!/usr/bin/env python2

#******************************************
#
#    SHARC Program Suite
#
#    Copyright (c) 2020 University of Vienna
#
#    This file is part of SHARC.
#
#    SHARC is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    SHARC is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    inside the SHARC manual.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************

#script to set up the first loop of the SHARC gym. In this loop the relevant normal modes and states of a given analytical Hamiltonian are determined. For the time being, Hamiltonian of the LVC-SHARC format are supported

import os
import re
import sys
import readline

Analyze_Modes={
  1: {'name':             'Final populations',
      'description':      'Compare final distribution at the last time step.'
     },
  2: {'name':             'Time-averaged per state deviation',
      'description':      'Deviation per state per time step averaged across the total time (Plasser et al.).'
     }
  }


# ======================================================================= #

def writefile(filename,content):
  # content can be either a string or a list of strings
  try:
    f=open(filename,'w')
    if isinstance(content,list):
      for line in content:
        f.write(line)
    elif isinstance(content,str):
      f.write(content)
    else:
      print 'Content %s cannot be written to file!' % (content)
      sys.exit(14)
    f.close()
  except IOError:
    print 'Could not write to file %s!' % (filename)
    sys.exit(2)

# ======================================================================= #

def readfile(filename):
  try:
    f=open(filename)
    out=f.readlines()
    f.close()
  except IOError:
    print 'File %s does not exist!' % (filename)
    sys.exit(1)
  return out

# ======================================================================= #

def question(question,typefunc,default=None,autocomplete=True,ranges=False):
  if typefunc==int or typefunc==float:
    if not default==None and not isinstance(default,list):
      print 'Default to int or float question must be list!'
      quit(1)
  if typefunc==str and autocomplete:
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")    # activate autocomplete
  else:
    readline.parse_and_bind("tab: ")            # deactivate autocomplete

  while True:
    s=question
    if default!=None:
      if typefunc==bool or typefunc==str:
        s+= ' [%s]' % (str(default))
      elif typefunc==int or typefunc==float:
        s+= ' ['
        for i in default:
          s+=str(i)+' '
        s=s[:-1]+']'
    if typefunc==str and autocomplete:
      s+=' (autocomplete enabled)'
    if typefunc==int and ranges:
      s+=' (range comprehension enabled)'
    s+=' '

    line=raw_input(s)
    line=re.sub('#.*$','',line).strip()
    if not typefunc==str:
      line=line.lower()

    if line=='' or line=='\n':
      if default!=None:
#        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return default
      else:
        continue

    if typefunc==bool:
      posresponse=['y','yes','true', 't', 'ja',  'si','yea','yeah','aye','sure','definitely']
      negresponse=['n','no', 'false', 'f', 'nein', 'nope']
      if line in posresponse:
#        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return True
      elif line in negresponse:
#        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return False
      else:
        print 'I didn''t understand you.'
        continue
    if typefunc==str:
#      KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
      return line

    if typefunc==float:
      # float will be returned as a list
      f=line.split()
      try:
        for i in range(len(f)):
          f[i]=typefunc(f[i])
#        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return f
      except ValueError:
        print 'Please enter floats!'
        continue

    if typefunc==int:
      # int will be returned as a list
      f=line.split()
      out=[]
      try:
        for i in f:
          if ranges and '~' in i:
            q=i.split('~')
            for j in range(int(q[0]),int(q[1])+1):
              out.append(j)
          else:
            out.append(int(i))
#        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return out
      except ValueError:
        if ranges:
          print 'Please enter integers or ranges of integers (e.g. "-3~-1  2  5~7")!'
        else:
          print 'Please enter integers!'
        continue

# ======================================================================= #

def what_to_analyze():
  '''Set the type of property to be analyzed. For now this is limited to 
  the options in populations.py. However, new entries can just be added.
  Adjustment in the later subroutines is needed. The number of the property 
  is returned.'''

  allowed=[i for i in range(1,23)]
#  print centerstring('Analyze Mode',60,'-')
  print '''\nThis script can analyze the classical populations in different ways:
1       Number of trajectories in each diagonal state                                   from output.lis
2       Number of trajectories in each (approximate) MCH state                          from output.lis
3       Number of trajectories in each (approximate) MCH state (multiplets summed up)   from output.lis
4       Number of trajectories whose total spin value falls into certain intervals      from output.lis
5       Number of trajectories whose dipole moment falls into certain intervals         from output.lis
6       Number of trajectories whose oscillator strength falls into certain intervals   from output_data/fosc.out

It can also sum the quantum amplitudes:
7       Quantum amplitudes in diagonal picture                                          from output_data/coeff_diag.out
8       Quantum amplitudes in MCH picture                                               from output_data/coeff_MCH.out
9       Quantum amplitudes in MCH picture (multiplets summed up)                        from output_data/coeff_MCH.out

It can also transform the classical diagonal populations to MCH basis:
12      Transform diagonal classical populations to MCH                                 from output_data/coeff_class_MCH.out
13      Transform diagonal classical populations to MCH (multiplets summed up)          from output_data/coeff_class_MCH.out
14      Wigner-transform classical diagonal populations to MCH                          from output_data/coeff_mixed_MCH.out
15      Wigner-transform classical diagonal populations to MCH (multiplets summed up)   from output_data/coeff_mixed_MCH.out 
It can also compute diabatic populations:
20      Quantum amplitudes in diabatic picture                                          from output_data/coeff_diab.out
21      Transform diagonal classical populations to diabatic                            from output_data/coeff_class_diab.out
22      Wigner-transform classical diagonal populations to diabatic                     from output_data/coeff_mixed_diab.out
'''

  while True:
    analyze_property=question('Which property should be analyzed? Select any of entries listed above by writing the corresponding number. The use of diabatic properties (20, 21, 22) is strongly suggested.',int)[0]
    if not analyze_property in allowed:
      print 'Please enter one of the following integers: %s!' % (allowed)
      continue
    break
  
  return analyze_property 


# ======================================================================= #

def read_input(input_path):
  print [input_path]
  setup_input = readfile(input_path)
  return setup_input


# ======================================================================= #

def run_populations(analyze_property, setup_input):
  '''Writes KEYSTROKES files for all directories that were set up and contain
  trajectories. '''
  
  base_dir = os.getcwd()
  for line in setup_input:
    curr_dir = line.split()[0]
    os.chdir(curr_dir)
    all_files = os.listdir(curr_dir)
    traj_dirs = []
    
    #get all directories that contain trajectories
    for file_name in all_files:
      if os.path.isdir(os.path.join(curr_dir, file_name)):
        test_dir = os.listdir((os.path.join(curr_dir, file_name)))
        for entry in test_dir:
          if 'TRAJ_' in entry:
            traj_dirs.append(file_name)
            break

    #write the KEYSTROKES file in the current directory
    keystrokes_pop = ''
    for directory in traj_dirs:
      keystrokes_pop += '%s\n' % directory
    keystrokes_pop += 'end\n'
    keystrokes_pop += '%i\n' %analyze_property
    if analyze_property in [6,7,8,9,12,13,14,15,20,21,22]:
      keystrokes_pop += 'False\n'
    keystrokes_pop += '\n\n'
    keystrokes_traj = readfile('KEYSTROKES.setup_traj_gym')
    max_time = 1000
    for line in keystrokes_traj:
      if 'Simulation time (fs)' in line:
        if len(line.split('#')) == 2:
          max_time = float(line.split('#')[0])
    keystrokes_pop += '%i\n'  % max_time
    keystrokes_pop += '\nTrue\n\nTrue\nTrue\n'
    writefile('KEYSTROKES.populations', keystrokes_pop)
    os.system('$SHARC/populations.py < KEYSTROKES.populations')
    
  os.chdir(base_dir)    

# ======================================================================= #    
    
def get_output_files(setup_input, analyze_file):    
  '''Reads in all setuped directories. Returns a dictionary that contains 
  the absolute path to all corresponding analyze_files if they do exist. 
  The reference file is determined by the user and marked with a dictionary
  value of 1.'''
  
  data_files = {}
  for line in setup_input:
    line = line.strip()
    if not os.path.isfile('%s/%s' % (line, analyze_file)):
      print 'No "%s" file found at %s' % (analyze_file, line)    
    else:
      data_files['%s/%s' % (line, analyze_file)] = [0]
      
  while True:
    path = question('Please select which "%s" file to use as a reference: ' % analyze_file,str)
    path = os.path.expanduser(os.path.expandvars(path))
    path = os.path.abspath(path)
    if os.path.isfile('%s/%s' % (path, analyze_file)):
      path = '%s/%s' % (path, analyze_file)
      break
    if analyze_file in path and os.path.isfile(path):
       break  
    print 'No "%s" file found at %s' % (analyze_file, path)
    continue

  data_files['%s' % path] = [1]
  
  return data_files
   
# ======================================================================= #

def adapt_removed_modes2analyzetype(removed_states, ref_states, analyze_property):
  '''Adapts the removed states to the desired analyze specifier. For example,
  if diagonal analysis is conducted, the removed states are added as containing 
  0 population after the population of all previous states. When doing analysis 
  in the diabatic picture however, the exact position of the missing states has
  to be determined.'''
  
  if analyze_property in [1,7]: #remove the last states
    total_states = sum([ int(ref_states[x])*(x+1) for x in range(len(ref_states))])
    removed_states = sum([ len(removed_states[x])*(x+1) for x in range(len(removed_states))])
    final_removed_states = []
    for i in range(removed_states):
      final_removed_states.append(total_states-i)
    final_removed_states.sort()
    
  elif analyze_property in [2,8,12,14]: #remove the last states in each multiplicity
    total_mn_states = [ ref_states[x]*(x+1) for x in range(len(ref_states)) ]
    removed_mn_states = [ len(removed_states[x])*(x+1) for x in range(len(removed_states)) ]
    #print total_mn_states, removed_mn_states
    final_removed_states = []
    sum_states = 0
    for i in range(len(removed_mn_states)):
      for j in range(removed_mn_states[i]):
        final_removed_states.append(total_mn_states[i]-j+sum_states)
      sum_states += total_mn_states[i]
    final_removed_states.sort()
    print final_removed_states
      
  elif analyze_property in [3,9,13,15]: #as before without expansion into multiplets
    total_mn_states =   ref_states 
    removed_mn_states = [ len(removed_states[x]) for x in range(len(removed_states))  ]
    final_removed_states = []
    sum_states = 0        
    for i in range(len(removed_mn_states)):
      for j in range(removed_mn_states[i]):
        final_removed_states.append(total_mn_states[i]-j+sum_states)
      sum_states += total_mn_states[i]
    final_removed_states.sort()
    #print final_removed_states

    
  elif analyze_property in [20,21,22]:
    #print "removed",removed_states
    removed_states_mn = []
    sum_states = 0
    for i in range(len(ref_states)):
      for state in removed_states[i]:
        for j in range(i+1):
          removed_states_mn.append(state+sum_states+j*int(ref_states[i]))
      sum_states += int(ref_states[i])   
    final_removed_states = removed_states_mn
    final_removed_states.sort()        
    #print final_removed_states 
  
  return final_removed_states 

# ======================================================================= #
      
def get_final_distribution(data_files, analyze_property, ref_LVC):
  '''Obtains the last line of the output files and compares those to the 
  reference data. The absolute deviation for all columns of properties 
  (except the first) is returned. The final data is the sum over all 
  deviations.'''

  results = []

  for key in data_files:
    if data_files[key][0] == 1:
      break
  ref_key = key

  lvc_data = ref_LVC
  ref_states = [ int(x) for x in lvc_data[1].split() ]
  if os.path.isfile('/'.join(key.split('/')[:-1]) + '/changed_parameters'):
    removed_modes, removed_states = read_removed_parameters(key,ref_states) 
    final_removed_states = adapt_removed_modes2analyzetype(removed_states, ref_states, analyze_property)
  else:
    final_removed_states = []
    removed_modes = []    
  ref = [ float(x) for x in readfile(key)[-1].split()]
  for state in final_removed_states: #insert in reference to max nr of states
    ref.insert(state, 0.0)  
  
  for key in data_files:
    if key == ref_key:
      continue
    tmp =  [ float(x) for x in readfile(key)[-1].split()]
    if os.path.isfile('/'.join(key.split('/')[:-1]) + '/changed_parameters'):
      removed_modes, removed_states = read_removed_parameters(key,ref_states) 
      final_removed_states = adapt_removed_modes2analyzetype(removed_states, ref_states, analyze_property)
    else:
      final_removed_states = []
      removed_modes = []
    data_files[ref_key].append(ref)    #what does this do?
    single_result = {}
    print tmp, final_removed_states
    for state in final_removed_states:
#      print tmp
      tmp.insert(state, 0.0)    
    print tmp
    single_result['complete_data'] = [ abs(ref[i]-tmp[i]) for i in range(len(tmp))][1:]
#    for state in final_removed_states:
#      print state
#      single_result['complete_data'].insert(state-1, 0.0)
    single_result['final_data'] = sum(single_result['complete_data'])
    single_result['category'] = key.split('/')[-3:-2]
    single_result['entry'] = key.split('/')[-2:-1]
    results.append(single_result)

  #sys.exit()

  return results

# ======================================================================= #

def  get_taverage_state_deviation(data_files, analyze_property, ref_LVC):
  '''Reads the complete output file and obtains the deviation from the 
  reference according to Plasser, Mai, Fumanal, Gindensperger, Daniel, 
  and Leticia Gonzalez, J. Chem. Theory Comput. 2019, 15, 9, 50315045. 
  The deviation normalized by time step and max time for all columns of 
  properties (except the first) is returned. The final data is the sum 
  over all deviations.'''
  
  results = [] 
  for key in data_files:
    if data_files[key][0] == 1:
      break
  ref_key = key
  lvc_data = ref_LVC  
  tmp_data = readfile(key)

  ref_states = [ int(x) for x in lvc_data[1].split() ]  
  if os.path.isfile('/'.join(key.split('/')[:-1]) + '/changed_parameters'):
    removed_modes, removed_states = read_removed_parameters(key,ref_states) 
    final_removed_states = adapt_removed_modes2analyzetype(removed_states, ref_states, analyze_property)
  else:
    final_removed_states = []
    removed_modes = []  
  ref_data = [ [ 0.0 for x in range(len(tmp_data[-1].split()))] for x in range(len(tmp_data)-3) ]
#  print len(ref_data[0])
  for i in range(len(ref_data)):
    for j in range(len(final_removed_states)): #extend dummy to max nr of states
      ref_data[i].append(0.0) 
#  print len(ref_data[0])      
  for i in range(len(tmp_data)):
    if '#' in tmp_data[i]:
      continue
    line_to_add = [ float(x) for x in tmp_data[i].split()]
    for state in final_removed_states:
      line_to_add.insert(state, 0.0)     #insert in reference to max nr of states
    ref_data[i-3] = line_to_add


    
  max_t = ref_data[-1][0]
  delta_t = ref_data[-1][0]-ref_data[-2][0]
  while True:
    max_t = question('Up to which time (fs) should the analysis be conducted?',float,[max_t])[0]
    if max_t%delta_t != 0:
      print max_t, delta_t
    break
  time_steps = int(max_t/delta_t)
  

  for key in data_files:
    if key == ref_key:
      continue   
    tmp_data =readfile(key)
    if os.path.isfile('/'.join(key.split('/')[:-1]) + '/changed_parameters'):
      removed_modes, removed_states = read_removed_parameters(key,ref_states) 
      final_removed_states = adapt_removed_modes2analyzetype(removed_states, ref_states, analyze_property)
    else:
      final_removed_states = []
      removed_modes = []   
         
    result_data = [ 0.0 for x in range(len(ref_data[0]))]
    for i in range(time_steps+4):
      if '#' in tmp_data[i]:
        continue      
      line_data = [ float(x) for x in tmp_data[i].split()]
      for state in final_removed_states:
        line_data.insert(state, 0.0)     #insert to increase to max nr of states      
      for j in range(len(line_data)):
        result_data[j] += abs(line_data[j]-ref_data[i-3][j])
    single_result = {}
    single_result['complete_data'] =  [ x*delta_t/max_t for x in result_data][1:]
    single_result['final_data'] = sum(single_result['complete_data'])
    single_result['category'] = key.split('/')[-3:-2]
    single_result['entry'] = key.split('/')[-2:-1]
    results.append(single_result)     

  return results
  
# ======================================================================= #

def print_results(result_files):
  '''for now just preliminary print function'''

  complete_print = True #TODO
  print "\n\n"
  #print result_files[0]
  print_category = []
  for entry in result_files:
    #print entry
    if not entry['category'] in print_category:
      print_category.append(entry['category'])
  print print_category
  complete_string = '+++% 30s  |  % 6s |  % 6s ---->' % ('Directory name', 'Total error', 'deviation per state')
  for category in print_category:
    print '---------------------------------------------------------------'
    print '-----%35s\n' % category[0]
    print complete_string
    complete_string += '\n'
    entries = []
    for entry in result_files:
      if category == entry['category']:
        entries.append(entry)
    final_entries = sorted(entries, key=lambda k: k['final_data']) 
    for entry in final_entries:
      s = '+++% 30s  |  % .6f   |' % (entry['entry'][0] ,entry['final_data'])
      if complete_print:
        for deviation in entry['complete_data']:
          s+= '% .6f  ' %   deviation
      print s 
      complete_string+= '%s\n' % s
  writefile("analysis_%s" % category[0], complete_string)

# ======================================================================= #

def get_directory():
  #Ask for the parent directory. Returns string that contains the absolute path
  #TODO for now only works in hamiltonian loop
  while True:
    path=question('Path to the parent directory of the calculations (hamiltonian_loop/parameter_loop) ',str)
    path=os.path.expanduser(os.path.expandvars(path))
    path=os.path.abspath(path)
    print path
    if not os.path.isdir(path):
      print 'Does not exist or is not a directory: %s' % (path)
      continue
    if not os.path.isfile('%s/setup_directories' % (path)):
      print 'No "setup_directories" file found at %s' % (path)
      continue
    base_dir = path
    break
  return base_dir

# ======================================================================= #

def read_removed_parameters(path, ref_states):
  #print path
  filename = '/'.join(path.split('/')[:-1]) + '/changed_parameters'
  param_data = readfile(filename)
  removed_modes = []
  removed_states = []  
  for i in range(len(param_data)):
    if 'removed_modes' in param_data[i]:
      try:
#      if all( isinstance(x, int) for x in param_data[i+1].split() ):
        removed_modes = [ int(x) for x in param_data[i+1].split() ]
        #print removed_modes
      except ValueError:
        print 'No removed modes found in file %s!' % path
   
#    if 'removed_states' in param_data[i]:
#      removed_states = []

    if 'Mult' in param_data[i]:
      removed_states.append([ int(x) for x in param_data[i].split()[2:] ])

  
  if removed_states == []:
    removed_states = [ [] for x in range(len(ref_states)) ]    
    
      
  return removed_modes, removed_states

# ======================================================================= #

def run_analyzer(setup_input, analyze_file, analyze_property, ref_LVC):
  '''Selection of which analyzer to use. New entries can just be added here'''
  
  print '\nPlease choose a method to analyze the chosen property:' 
  cando=list(Analyze_Modes)
  for i in Analyze_Modes:
    print '%i\t%s' % (i, Analyze_Modes[i]['description'])
  while True:
    analyze=question('Choose a mode to analyze the chosen property:',int,[2])[0]
    if analyze in Analyze_Modes and analyze in cando:
      break
    else:
      print 'Please input one of the following: %s!' % ([i for i in cando])

  if analyze in [1,2]: #make multiple analyses at once possible?
    data_files = get_output_files(setup_input, analyze_file)
    if analyze == 1:
      result_files = get_final_distribution(data_files, analyze_property, ref_LVC)
    elif analyze == 2:
      result_files = get_taverage_state_deviation(data_files, analyze_property, ref_LVC)

  return result_files

# ======================================================================= #

def main():


  base_dir = get_directory()
  setup_input = read_input('%s/setup_directories' % base_dir)
  ref_LVC = readfile('%s/LVC.template' %base_dir) 

#  need_properties = question('Are the properties already extracted?',bool,True):  TODO 

  analyze_property = what_to_analyze()
  #new analyze modes can be put in with higher numbers than 22
  if analyze_property < 23 :
    run_populations(analyze_property, setup_input)
    analyze_file = 'pop.out'

  result_files = run_analyzer(setup_input, analyze_file, analyze_property, ref_LVC)


  print_results(result_files)




# ======================================================================= #


main()




