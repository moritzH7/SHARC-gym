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
import shutil
import readline
from copy import deepcopy
from itertools import combinations

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

def read_input(input_path):
  setup_input = readfile(input_path)
  return setup_input

# ======================================================================= #

def write_run_data_extractor(base_dir, netcdf):
  #TODO missing default SHARC
  s = '#!/bin/bash\n\n'
  s += '. $SHARC/sharcvars.sh\n'
  if netcdf:
    s += '$SHARC/data_extractor_NetCDF.x output.dat\n'
  else:
    s += '$SHARC/data_extractor.x output.dat\n' 
  writefile('%s/run_data_extractor.sh' % base_dir, s)

# ======================================================================= #

def run_excite(setup_input):


  directories = [ line for line in setup_input ]      
  if os.getcwd().split('/')[-1] == 'hamiltonian_loop':
    current_loop = 1
  elif os.getcwd().split('/')[-1] == 'parameter_loop':
    current_loop = 2
#    directories.insert(0, os.getcwd() ) #make sure that the first directory is the base dir    

  #print 'directories', directories

  diab = False 
  qsub = False
  first_excite = True
  base_dir = os.getcwd()
  for line in directories:

    if first_excite:
      extract_output =  open('%s/gym_extract_output_traj.sh' % base_dir,'w')
      if current_loop == 1:
        os.chdir(line.split()[0])      
        key_dir = os.getcwd()  
        os.system('$SHARC_GYM/mod_excite.py --sharc_gym')                 
        os.system('$SHARC_GYM/mod_setup_traj.py --sharc_gym')
        extract_output.write('#!/bin/bash\n\n')
        keystrokes_traj = readfile('%s/KEYSTROKES.setup_traj_gym' % key_dir)
      elif current_loop == 2:
        key_dir = base_dir   
        os.system('$SHARC_GYM/mod_excite.py --sharc_gym')                         
        os.chdir(line.split()[0])    
        curr_dir = os.getcwd()       
        keystrokes_traj = readfile('%s/KEYSTROKES.setup_traj_gym' % directories[0].split()[0]) 
        shutil.copyfile('%s/initconds.excited' % base_dir , '%s/initconds.excited' % curr_dir)
        shutil.copyfile('%s/LVC.template' % base_dir , '%s/LVC.template' % curr_dir)        
        os.system('$SHARC_GYM/mod_setup_traj.py --sharc_gym < %s/KEYSTROKES.setup_traj_gym' % curr_dir)        

        
      curr_dir = os.getcwd()    
      netcdf = False
      for i in range(len(keystrokes_traj)):
        print keystrokes_traj[i]
        if 'Write output in NetCDF format' in keystrokes_traj[i]:
          if keystrokes_traj[i].split('#')[0].strip().lower() not in ['n','no', 'false', 'f', 'nein', 'nope', False]: 
            print "netcdf"
            netcdf = True
        if 'Generate submission script' in keystrokes_traj[i]:
          if keystrokes_traj[i].split('#')[0].strip().lower() in ['y','yes','true', 't', 'ja',  'si','yea','yeah','aye','sure','definitely', True]:
            qsub = True
            all_qsub = open('%s/gym_all_qsub_traj.sh' % base_dir,'w')
            all_qsub.write('#!/bin/bash\n\n')   
        if 'Submission command' in keystrokes_traj[i]:
          qsub_command = keystrokes_traj[i].split('#')[0] #TODO are there scripts where this is a problem?                     
      #print qsub_command, qsub
      #sys.exit()
      if qsub == False:
        all_run = open('%s/gym_all_run_traj.sh' % base_dir,'w')
        all_run.write('#/bin/bash\n\n')
        qsub_command = 'bash  '
      keystrokes_excite = readfile('%s/KEYSTROKES.excite_gym' % key_dir)
      for i in range(len(keystrokes_excite)):
        if 'Do you want to specify the initial states in a diabatic picture' in keystrokes_excite[i]:
          if keystrokes_excite[i].split()[0] in ['y','yes','true', 't', 'ja',  'si','yea','yeah','aye','sure','definitely']:
            diab = True
            target_state = int(keystrokes_excite[i+1].split()[0]) #can only take a single diabatic start state
      first_excite = False
    else:
      os.chdir(line.split()[0])    
      curr_dir = os.getcwd()          
      if current_loop == 1:
        os.system('$SHARC_GYM/mod_excite.py --sharc_gym < %s/KEYSTROKES.excite_gym' % key_dir)
        os.system('$SHARC_GYM/mod_setup_traj.py --sharc_gym < %s/KEYSTROKES.setup_traj_gym' % key_dir)        
      elif current_loop == 2:
        shutil.copyfile('%s/initconds.excited' % base_dir , '%s/initconds.excited' % curr_dir)
        shutil.copyfile('%s/LVC.template' % base_dir , '%s/LVC.template' % curr_dir)        
        os.system('$SHARC_GYM/mod_setup_traj.py --sharc_gym < %s/KEYSTROKES.setup_traj_gym' % curr_dir)      
    if qsub:
      print '%s/gym_all_qsub_traj.sh' % base_dir
      all_qsub.write('bash %s/all_qsub_traj.sh\n\n' % curr_dir)
#      sys.exit()      
    else:
      all_run.write('bash %s/all_run_traj.sh\n\n' % curr_dir)
    print "Setting links for diabatisation..."
    for entry in os.walk(curr_dir):
      sub_dir =  entry[0].split('/')[-1]
      if "TRAJ" in sub_dir:
        if not os.path.exists('%s/Reference' % entry[0] ):  #add reference for diabatization 
          try:
            if current_loop == 1:
              os.symlink('%s/ICOND_%s' % (curr_dir,sub_dir.split('_')[-1]), '%s/Reference' % entry[0] )
            if current_loop == 2:
              os.symlink('%s/ICOND_%s' % (base_dir,sub_dir.split('_')[-1]), '%s/Reference' % entry[0] )
          except OSError:
            pass
        if qsub:
          extract_output.write('cd %s\n  %s   %s/run_data_extractor.sh\n\n' % (entry[0], qsub_command, base_dir))

        #initialize pure diabatic state population
        if diab:
          if current_loop == 1:
            qm_out = readfile('%s/ICOND_%s/QM.out' % (curr_dir,sub_dir.split('_')[-1]))
          elif current_loop == 2:
            qm_out = readfile('%s/ICOND_%s/QM.out' % (base_dir,sub_dir.split('_')[-1]))
          for i in range(len(qm_out)):
            if 'Overlap matrix' in qm_out[i]:
              state_overlap = qm_out[i+target_state+1].split()
              break
          coeff_string = ''
          for i in range(len(state_overlap)/2):
            coeff_string += '%s  %s\n' % (state_overlap[i*2], state_overlap[i*2+1])
          writefile('%s/coeff' %entry[0], coeff_string)
          input_file = readfile('%s/input' % entry[0])
          for i in range(len(input_file)):
            if 'coeff auto' in input_file[i]:
              input_file[i] = 'coeff external\n'
          input_string = ''
          for line in input_file:
            input_string += line
          writefile('%s/input' % entry[0], input_string)
     


  if qsub:
    all_qsub.close()
  else:
    all_run.close()
  extract_output.close()
  #sys.exit()    

  write_run_data_extractor(base_dir, netcdf)


# ======================================================================= #


def main():
  while True:
    path=question('Path to the parent directory of the calculations (hamiltonian_loop/parameter_loop) that contains the "setup_directories" file: ',str)
    path=os.path.expanduser(os.path.expandvars(path))
    if not os.path.isdir(path):
      print 'Does not exist or is not a directory: %s' % (path)
      continue
    if not os.path.isfile('%s/setup_directories' % path):
      print 'No "setup_directories" file found at %s' % (path)
      continue
    base_dir = path
    break

  setup_input = read_input('%s/setup_directories' % path)
  print setup_input
  run_excite(setup_input)




# ======================================================================= #

main()

