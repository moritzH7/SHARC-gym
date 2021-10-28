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

'''script to set up the loops of the SHARC gym. 
In the Hamiltonian loop the relevant normal modes and states of a given analytical Hamiltonian are determined. In the Parameter loop, a set of ideal surface hopping parameters can be obtained.
For the time being, Hamiltonians of the LVC-SHARC format are supported'''

import os
import re
import sys
import shutil
import readline
import itertools
from copy import deepcopy
from itertools import combinations

#globally defined dictionaries used in the interactive interface

Loops={
  1: {'name':             'Hamiltonian loop',
      'description':      'Loop to reduce the hamiltonian either in normal modes or states.',
      'dir_name':         'hamiltonian_loop'
     },
  2: {'name':             'Parameter loop',
      'description':      'Loop to determine influence of surface hopping parameters.',
      'dir_name':         'parameter_loop'
     }
  }

Couplings={
  1: {'name':        'nacdt',
      'description': 'DDT     =  < a|d/dt|b >        Hammes-Schiffer-Tully scheme (not available)   '
     },
  2: {'name':        'nacdr',
      'description': 'DDR     =  < a|d/dR|b >        Original Tully scheme          '
     },
  3: {'name':        'overlap',
      'description': 'overlap = < a(t0)|b(t) >       Local Diabatization scheme     '
     }
  }

EkinCorrect={
  1: {'name':             'none',
      'description':      'Do not conserve total energy. Hops are never frustrated.',
      'description_refl': 'Do not reflect at a frustrated hop.',
      'required':   []
     },
  2: {'name':             'parallel_vel',
      'description':      'Adjust kinetic energy by rescaling the velocity vectors. Often sufficient.',
      'description_refl': 'Reflect the full velocity vector.',
      'required':   []
     },
  3: {'name':             'parallel_nac',
      'description':      'Adjust kinetic energy only with the component of the velocity vector along the non-adiabatic coupling vector.',
      'description_refl': 'Reflect only the component of the velocity vector along the non-adiabatic coupling vector.',
      'required':   ['nacdr']
     },
  4: {'name':             'parallel_diff',
      'description':      'Adjust kinetic energy only with the component of the velocity vector along the gradient difference vector.',
      'description_refl': 'Reflect only the component of the velocity vector along the gradient difference vector.',
      'required':   []
     }
  }

Decoherences={
  1: {'name':             'none',
      'description':      'No decoherence correction.',
      'required':   [],
      'params':     ''
     },
  2: {'name':             'edc',
      'description':      'Energy-based decoherence scheme (Granucci, Persico, Zoccante).',
      'required':   [],
      'params':     '0.1'
     },
  3: {'name':             'afssh',
      'description':      'Augmented fewest-switching surface hopping (Jain, Alguire, Subotnik).',
      'required':   [],
      'params':     ''
     }
  }

HoppingSchemes={
  1: {'name':             'off',
      'description':      'Surface hops off.'
     },
  2: {'name':             'sharc',
      'description':      'Standard SHARC surface hopping probabilities (Mai, Marquetand, Gonzalez).'
     },
  3: {'name':             'gfsh',
      'description':      'Global flux surface hopping probabilities (Wang, Trivedi, Prezhdo).'
     }
  }

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
        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return default
      else:
        continue

    if typefunc==bool:
      posresponse=['y','yes','true', 't', 'ja',  'si','yea','yeah','aye','sure','definitely']
      negresponse=['n','no', 'false', 'f', 'nein', 'nope']
      if line in posresponse:
        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return True
      elif line in negresponse:
        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return False
      else:
        print 'I didn''t understand you.'
        continue

    if typefunc==str:
      KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
      return line

    if typefunc==float:
      # float will be returned as a list
      f=line.split()
      try:
        for i in range(len(f)):
          f[i]=typefunc(f[i])
        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
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
        KEYSTROKES.write(line+' '*(40-len(line))+' #'+s+'\n')
        return out
      except ValueError:
        if ranges:
          print 'Please enter integers or ranges of integers (e.g. "-3~-1  2  5~7")!'
        else:
          print 'Please enter integers!'
        continue

# ======================================================================= #

def open_keystrokes():
  global KEYSTROKES
  KEYSTROKES=open('KEYSTROKES.tmp','w')

# ======================================================================= #

def close_keystrokes():
  KEYSTROKES.close()
  shutil.move('KEYSTROKES.tmp','KEYSTROKES.SHARC_gym')

# ======================================================================= #

def read_input(input_file):
  '''reads the inputfile sharc_gym.in which contains extra keywords for the 
  sharc-gym (number of states, algorithm to reduce states and normal modes, 
  number of desired properties, etc)
  Arguments: 
  1 string: name of the input file
  
  Returns:
  1 dictionary:  sharc_gym_input'''

  
  input_data = readfile(input_file)
  sharc_gym_input = {}
  i = -1
    
  while i+1 != len(input_data):
    i+=1
    line=input_data[i]
    line=re.sub('#.*$','',line)
    if len(line.split())==0:
        continue
    key=line.lower().split()[0]
    args=line.split()[1:]
    if key in sharc_gym_input:
        print 'Repeated keyword %s in line %i in input file! Check your input!' % (key,i+1)
        continue  # only first instance of key takes effect

    sharc_gym_input[key]=args

  print sharc_gym_input

  return sharc_gym_input

# ======================================================================= #

def read_hamiltonian(lvc_file):
  #reads the given LVC Hamiltonian
  lvc_data = readfile(lvc_file)
  ref_hamiltonian = { 'v0' : lvc_data[0].strip() ,
                  'states' : [ int(x) for x in lvc_data[1].split() ] }
  ref_hamiltonian['nr_states'] = sum([ int(ref_hamiltonian['states'][x])*(x+1) for x in range(len(ref_hamiltonian['states']))])
  print ref_hamiltonian['states'], ref_hamiltonian['nr_states']

  keywordlist_linear = ['epsilon', 'kappa', 'lambda']
  keywordlist_matrix = ['SOC R', 'SOC I', 'DMX R', 'DMY R', 'DMZ R', 'DMX I', 'DMY I', 'DMZ I']


  #here we just get the modes that have some coupling elements
  #The LVC template does not contain the number of used modes per se
  #However, we only care for the modes that actually do something
  used_modes = []
  for i in range(len(lvc_data)):
    if 'kappa' in lvc_data[i]:
      for j in range(int(lvc_data[i+1].split()[0])):
        current_mode = int(lvc_data[i+2+j].split()[2])
        if current_mode in used_modes:
          continue
        used_modes.append(current_mode)

  for i in range(len(lvc_data)):
    if 'lambda' in lvc_data[i]:
      for j in range(int(lvc_data[i+1].split()[0])):
        current_mode = int(lvc_data[i+2+j].split()[3])
        if current_mode in used_modes:
          continue
        used_modes.append(current_mode)
  used_modes.sort()
  ref_hamiltonian['used_modes'] = used_modes


  line_nr = 2 #the first two lines have a fixed format so we can read them directly
  while line_nr < len(lvc_data):

  #loop over the file until a keyword is recognized. 
  #For kappa and lambda, the number of elements is written below the corresponding keyword
  #all other keywords have nr_states entries. All inline comments are kept
    

    if any( keyword in lvc_data[line_nr].lower() for keyword in keywordlist_linear ):
      current_keyword = lvc_data[line_nr].lower().strip()
      print current_keyword
      line_nr += 1      
      nr_entries = int(lvc_data[line_nr].split()[0])
      ref_hamiltonian[current_keyword] = [ [] for x in range(nr_entries) ]
      print nr_entries
      for i in range(nr_entries):
        ref_hamiltonian[current_keyword][i] = lvc_data[line_nr+1+i]#the +1 accounts for the line below the keyword
      line_nr += nr_entries+1
      continue


    if any( keyword in lvc_data[line_nr].upper() for keyword in keywordlist_matrix ):
      current_keyword = lvc_data[line_nr].upper().strip()
      print current_keyword
      line_nr += 1      
      ref_hamiltonian[current_keyword] = [ [] for x in range(ref_hamiltonian['nr_states'])]
      for i in range(ref_hamiltonian['nr_states']):
        ref_hamiltonian[current_keyword][i] = lvc_data[line_nr+i]
      line_nr += ref_hamiltonian['nr_states']
      continue
    
    line_nr += 1


  return ref_hamiltonian

# ======================================================================= #

def reduce_hamiltonian(ref_hamiltonian, keep_modes, keep_states): 
  #takes the hamiltonian dictionary, a list of states and a list of modes
  #it creates a new dictionary where all entries and matrix elements of unwanted states and modes are removed
  #States are being renumbered in this process

  keywordlist_linear = ['epsilon', 'kappa', 'lambda']
  keywordlist_matrix = ['SOC R', 'SOC I', 'DMX R', 'DMY R', 'DMZ R', 'DMX I', 'DMY I', 'DMZ I']

  adapted_hamiltonian = deepcopy(ref_hamiltonian)

  #the first three can be put in a single smart function (that I dont know)
  print keep_states
  epsilons = []
  for i in range(len(adapted_hamiltonian['epsilon'])):
    line = adapted_hamiltonian['epsilon'][i].split()
    if int(line[1]) not in keep_states[int(line[0])-1]:
      adapted_hamiltonian['epsilon'][i] = 'deleted\n'
    else:
      line[1] = str(keep_states[int(line[0])-1].index(int(line[1]))+1)
      epsilons.append('  %i   %i % .5e\n' % (int(line[0]), int(line[1]), float(line[2])))
  adapted_hamiltonian['epsilon'] = epsilons

  kappas = []
  for i in range(len(adapted_hamiltonian['kappa'])):
    line = adapted_hamiltonian['kappa'][i].split()
    if int(line[1]) not in keep_states[int(line[0])-1] or (int(line[2]) not in keep_modes):
      adapted_hamiltonian['kappa'][i] = 'deleted\n'
    else:
      line[1] = str(keep_states[int(line[0])-1].index(int(line[1]))+1)
      kappas.append('  %i   %i     %i % .5e\n' % (int(line[0]), int(line[1]), int(line[2]), float(line[3])))
  adapted_hamiltonian['kappa'] = kappas

  lambdas = []
  for i in range(len(adapted_hamiltonian['lambda'])):
    line = adapted_hamiltonian['lambda'][i].split()
    if int(line[1]) not in keep_states[int(line[0])-1] or int(line[2]) not in keep_states[int(line[0])-1] or (int(line[3]) not in keep_modes):
      adapted_hamiltonian['lambda'][i] = 'deleted\n'
    else:
      line[1] = str(keep_states[int(line[0])-1].index(int(line[1]))+1)
      line[2] = str(keep_states[int(line[0])-1].index(int(line[2]))+1)      
      lambdas.append('  %i   %i   %i   %i % .5e\n' % (int(line[0]), int(line[1]), int(line[2]), int(line[3]), float(line[4])))
  adapted_hamiltonian['lambda'] = lambdas

  #transform keep_states into a set of states that includes the multiplicity
  keep_states_mn = []
  sum_states = 0
  for i in range(len(ref_hamiltonian['states'])):
    for state in keep_states[i]:
      for j in range(i+1):
        keep_states_mn.append(state+sum_states+j*int(ref_hamiltonian['states'][i]))
    sum_states += int(ref_hamiltonian['states'][i])

  #delete unwanted matrix entries
  for keyword in keywordlist_matrix:
    if keyword in ref_hamiltonian.keys():
      adapted_property = []
      for i in range(len(adapted_hamiltonian[keyword])):
        line = adapted_hamiltonian[keyword][i].split()
        new_line = []
        if i+1 not in keep_states_mn:
          continue
        for j in range(len(line)):
          if j+1 in keep_states_mn:
            new_line.append(line[j])
        adapted_line = ''
        for element in new_line:
          adapted_line += '% .7e ' % float(element)
        adapted_line += '\n'
        adapted_property.append(adapted_line)
      adapted_hamiltonian[keyword] = deepcopy(adapted_property)
    
  adapted_hamiltonian['states'] = [ len(x) for x in keep_states]

  return adapted_hamiltonian

   
      
    

# ======================================================================= #
def write_hamiltonian(hamiltonian, outfile): 
  #write an instance of a reduced or not reduced Hamiltonian into a new LVC template

  keywordlist_linear = ['epsilon', 'kappa', 'lambda']
  keywordlist_matrix = ['SOC R', 'SOC I', 'DMX R', 'DMY R', 'DMZ R', 'DMX I', 'DMY I', 'DMZ I']

  output_string = ''
  output_string += '%s\n' % hamiltonian['v0']
  for state in hamiltonian['states']:
    output_string += '%s ' % state
  output_string += '\n'

  for keyword in keywordlist_linear:
    output_string += '%s\n%i\n' % (keyword,len(hamiltonian[keyword]) )
    for entry in hamiltonian[keyword]:
      output_string += '%s' %entry


  for keyword in keywordlist_matrix:
    if keyword in hamiltonian.keys():
      output_string += '%s\n' % keyword
      for entry in hamiltonian[keyword]:
        output_string += '%s' %entry
    else:
      continue
  

  #print output_string
  writefile(outfile, output_string)

# ======================================================================= #

def mode_selection(sharc_gym_input, ref_hamiltonian):
  '''Performs a selection of normal modes based on various approaches.
  After selection, a dictionary is returned which contains all to-be-performed sets of normal modes
  Arguments: 
  1 dictionary: parsed input file
  2 dictionary: parsed LVC hamiltonian
  
  Returns:
  1 dictionary:  Sets of normal modes'''


  final_modes = {}  
  if 'mode_selector' in sharc_gym_input:

    if sharc_gym_input['mode_selector'][0].lower() == 'none':
      final_modes['all'] = [ref_hamiltonian['used_modes']]    
      pass

    elif sharc_gym_input['mode_selector'][0].lower() == 'all':
      print 'Generating all possible mode combinations ordered according to the number of normal modes.'
      final_modes = exhaustive_mode_combination(ref_hamiltonian['used_modes'], len(ref_hamiltonian['used_modes']))

    elif sharc_gym_input['mode_selector'][0].lower() == 'depth':
      print 'Generating all possible mode combinations up to a depth of n-%i normal modes.' % int(sharc_gym_input['mode_selector'][1])
      final_modes = exhaustive_mode_combination(ref_hamiltonian['used_modes'], int(sharc_gym_input['mode_selector'][1])+1)
  else:
    final_modes['all'] = [ref_hamiltonian['used_modes']]


  #print final_modes
  return final_modes
  
# ======================================================================= #
  
def state_selection(sharc_gym_input, ref_hamiltonian):
  '''Performs a selection of states based on various approaches.
  After selection, a dictionary is returned which contains all to-be-performed sets of states
  Arguments: 
  1 dictionary: parsed input file
  2 dictionary: parsed LVC hamiltonian  
  
  Returns:
  1 dictionary:  Sets of states'''
  
  keep_states = [[1,2],[],[]] #TODO
    
  final_states = {}
  if 'state_selector' in sharc_gym_input:

    if sharc_gym_input['state_selector'][0].lower() == 'none':
      state_list = [ [] for x in range(len(ref_hamiltonian['states'])) ]
      for x in range(len(ref_hamiltonian['states'])):
        for k in range(int(ref_hamiltonian['states'][x])):
          state_list[x].append(k+1)
      final_states['all'] = [state_list]
      pass

    elif sharc_gym_input['state_selector'][0].lower() == 'all':
      print 'Generating all possible state combinations ordered according to the number of normal states.'
      final_states = exhaustive_state_combination(ref_hamiltonian['states'], sum([ sum(x) for x in states ]), keep_states)

    elif sharc_gym_input['state_selector'][0].lower() == 'depth':
      print 'Generating all possible state combinations up to a depth of n-%i states.' % int(sharc_gym_input['state_selector'][1])
      final_states = exhaustive_state_combination(ref_hamiltonian['states'], int(sharc_gym_input['state_selector'][1])+1, keep_states)  
  else:
    state_list = [ [] for x in range(len(ref_hamiltonian['states'])) ]
    for x in range(len(ref_hamiltonian['states'])):
      for k in range(int(ref_hamiltonian['states'][x])):
        state_list[x].append(k+1)
    final_states['all'] = [state_list]
      
  #print final_states

  return final_states 

# ======================================================================= #

def exhaustive_mode_combination(used_modes, depth):
  #returns a dictionary containing all combinations of modes down to n-depth
  final_modes = {}
  for i in range(depth):
    current_depth = len(used_modes) - i
    final_modes['depth_%i' % i] = sub_lists(used_modes, current_depth)
  
  return final_modes


# ======================================================================= #

def exhaustive_state_combination(states, depth, keep_states):
  '''Generates all needed combinations of states where the requested number 
  of states has been removed. Each state combination that will be set up is 
  a list of list where each sublist represents the corresponding multiplicity.
  Each sublist contains the states that will be kept in this multiplicity. 
  A state combination like [[1,3],[],[2]] means that only the first and third 
  singlet states as well as the second triplet state will be written to the new 
  LVC.template file.
  Arguments: 
  1 list:        List of states, eg [4, 0, 3]
  2 integer:     How many states should be removed at max
  3 keep_states: List of lists, identical to the state combination format
  
  Returns:
  1 dictionary:  Sets of state combinations'''
  
  final_states = {}
  
  #get a single unnested list containing all states numbered from one to max-state
  #also expand keep states corespondingly
  expand_states = [ i+1 for i in range(sum(states)) ]
  transformed_keep_states = []
  sum_states = 0
  for i in range(len(keep_states)):
    for j in range(len(keep_states[i])):
      transformed_keep_states.append(keep_states[i][j]+sum_states)
    sum_states += states[i]

  #remove keep_states from the list of avilable states for which the redcution 
  #will be performed    
  iterate_states = [ x for x in expand_states if x not in transformed_keep_states]

  #generate all combinations
  for i in range(depth):
    current_depth = len(iterate_states) -i
    tmp_lists = sub_lists(iterate_states, current_depth)
    adapted_states = []
    #transform list back to list of lists with unique numbering only inside
    #the same multiplicity
    for add_list in tmp_lists:
      #add keep_states again
      for keep_state in transformed_keep_states:
        add_list.append(keep_state)
      tmp = [ [] for x in range(len(states)) ]
      sum_states = 0
      state_numbers = 0
      for j in range(len(states)):
        sum_states += states[j]
        for k in range(len(add_list)):
          if add_list[k] <= sum_states and add_list[k]-state_numbers > 0:
            tmp[j].append(add_list[k]-state_numbers)
        tmp[j].sort()            
        state_numbers += states[j]
      add_list = tmp
      adapted_states.append(tmp)

    final_states['depth_%i' % i ] = adapted_states

  return final_states

# ======================================================================= #

def sub_lists(my_list, depth):
  #Generates all non-redundant subsets of elements in a given list up to order n-depth
  subs = [list(x) for x in combinations(my_list, depth)]
  return subs

# ======================================================================= #

def setup_first_directory(base_dir):
  nr_init = question('How many initial conditions do you want to set up? ',int,[10])[0]
  os.system('python2 $SHARC_GYM/mod_wigner.py -n %i  init.molden' % nr_init)
  os.system('$SHARC_GYM/mod_setup_init.py --sharc_gym')  
  key_dir = os.getcwd()

  return key_dir, nr_init


# ======================================================================= #

def setup_dynamics(ref_hamiltonian, freq, final_modes, final_states, parameters, current_loop):

  all_states = [ [] for x in ref_hamiltonian['states']]  
  for x in range(len(ref_hamiltonian['states'])):
    for k in range(int(ref_hamiltonian['states'][x])):
      all_states[x].append(k+1)

  print 'all_states', all_states


  #generate the requested loop directory and sets up the files needed to proceed
  print 'Setting up the calculations...\n'
  if current_loop == 1:
    make_directory('hamiltonian_loop')
    os. chdir('hamiltonian_loop')
  elif current_loop == 2:
    make_directory('parameter_loop')
    os. chdir('parameter_loop')

  base_dir = os.getcwd()
  final_directories = open('setup_directories', 'w')
  write_hamiltonian(ref_hamiltonian,'LVC.template')
 # print final_modes

  if current_loop == 1:
    first_dir = True
    for key in final_modes:
      #make_directory('%s' % key)
      #os. chdir('%s' % key)
      for mode_combination in final_modes['%s' % key]:       
        changed_modes =  [x for x in ref_hamiltonian['used_modes'] if x not in mode_combination]
        dir_string = 'mminus_'
        for mode in changed_modes:
          dir_string += str(mode)
        #sys.exit()
        for key in final_states:
          #print final_states, key
          for state_combination in final_states['%s' % key]:
            all_states_diff = []
            state_string = 'sminus'          
            for i in range(len(all_states)):
              print all_states, state_combination
              changed_states = [x for x in all_states[i] if x not in state_combination[i]] 
              state_string += '_'              
              all_states_diff.append(changed_states)
              if len(changed_states) != 0:         
                for state in changed_states:
                  state_string += str(state)
              else:
                state_string += '0'
            final_dir_string = dir_string + state_string  
                                                 
            make_directory('%s' % final_dir_string)
            os. chdir('%s' % final_dir_string)
            reduced_hamiltonian = reduce_hamiltonian(ref_hamiltonian, mode_combination, state_combination)
            write_removed_parameters(changed_modes, all_states_diff)
            write_hamiltonian(reduced_hamiltonian, 'LVC.template') 
            mod_molden(freq, changed_modes, 'init.molden')
        #run the default set up scripts for the first directory. All other 
        #directories use the KEYSTROKES files generated there
            if first_dir:
              key_dir, nr_init = setup_first_directory(base_dir)
              diabatic_check = readfile('%s/ICOND_00001/run.sh' % key_dir) 
              for line in diabatic_check:
                if "Should do a reference overlap calculation" in line:
                  diabat = True
                  all_first_run = open('%s/gym_all_run_first_init.sh' % base_dir,'w')
                  all_first_run.write('#/bin/bash\n\n')
                  break
                else:
                  diabat = False
              if os.path.isfile('%s/all_qsub_init.sh' % key_dir):
                qsub = True
                all_qsub = open('%s/gym_all_qsub_init.sh' % base_dir,'w')
                all_qsub.write('#/bin/bash\n\n')
              else:
                qsub = False
                all_run = open('%s/gym_all_run_init.sh' % base_dir,'w')
                all_run.write('#/bin/bash\n\n')
              first_dir = False
            else:
              os.system('python2 $SHARC_GYM/mod_wigner.py -n %i  init.molden' % nr_init)
              os.system('$SHARC_GYM/mod_setup_init.py --sharc_gym < %s/KEYSTROKES.setup_init_gym' % key_dir)  
            current_dir = os.getcwd()
            if diabat:
              all_first_run.write('cd %s/ICOND_00000\nbash run.sh\n\n' % current_dir)   
            if qsub:
              all_qsub.write('bash %s/all_qsub_init.sh\n\n' % current_dir)
            else:
              all_run.write('bash %s/all_run_init.sh\n\n' % current_dir)
            final_directories.write('%s\n' % current_dir)
            os. chdir('../')      #TODO this can go wrong easily  
      #os. chdir('../')      
    os. chdir('../')  
    if diabat:
      all_first_run.close()
    if qsub:
      all_qsub.close()
    else:
      all_run.close()
    final_directories.close()

  elif current_loop == 2:
    reduced_hamiltonian = reduce_hamiltonian(ref_hamiltonian, final_modes, final_states)
    write_hamiltonian(reduced_hamiltonian, 'LVC.template') 
    mod_molden(freq, [], 'init.molden')
    key_dir, nr_init = setup_first_directory(base_dir)
    for combination in parameters['combinations']:
      dir_string = 'traj_'
      for option in combination:
        dir_string += str(option)[0]
      make_directory('%s' % dir_string)
      write_keystrokes_traj(parameters, combination, dir_string)
      final_directories.write('%s/%s\n' % (base_dir,dir_string) )
    os.chdir('../')


# ======================================================================= # 

def write_removed_parameters(changed_modes, changed_states):
  #write all removed parameters in the directory with the changed LVC-template
  write_string = ''
  if len(changed_modes) > 0:
    write_string += 'removed_modes\n'
    for mode in changed_modes:
      write_string += '%i ' % mode
    write_string += '\n'
  if any(len(x) > 0 for x in changed_states):
    write_string += 'removed_states\n'
    for i in range(len(changed_states)):
      write_string += 'Mult %i: ' % (i+1)
      for state in changed_states[i]:
        write_string += '%i ' % state
      write_string += '\n'
  writefile('changed_parameters', write_string)
    
# ======================================================================= # 

def write_keystrokes_traj(parameters, combination, dir_string):
  '''For the parameter loop, a keystrokes file is written for every set of
  chosen options'''
  
  keystrokes_string = ''
  keystrokes_string += '%s\n' % parameters['rng']
  keystrokes_string += '%f\n' % parameters['tmax']
  keystrokes_string += '%f\n' % parameters['dtstep']
  keystrokes_string += '%i\n' % parameters['nsubstep']
  keystrokes_string += '%s\n' % str(parameters['kill'])
  if parameters['kill']:
    keystrokes_string += '%f\n' % parameters['killafter']
  keystrokes_string += '%s\n' % str(combination[0])
  keystrokes_string += '%s\n' % str(parameters['soc'])
  keystrokes_string += '%s\n' % str(combination[1])
  if combination[1] != 3:
    keystrokes_string += 'True\n'
  if combination[0]:
    keystrokes_string += 'True\n'
  keystrokes_string += '%s\n' % str(combination[2])  
  keystrokes_string += '%s\n' % str(combination[3])
  keystrokes_string += '%s\n' % str(combination[4])
  keystrokes_string += '%s\n' % str(combination[5])
  keystrokes_string += '%s\n' % str(parameters['force_hops'])
  if parameters['force_hops']:
    keystrokes_string += '%s\n' % str(parameters['force_hops_dE'])
  keystrokes_string += '%s\n' % str(parameters['scaling'])
  keystrokes_string += '%s\n' % str(parameters['damping'])
  if combination[4] == 2 or combination[2] == 2 or combination[3] == 2:
    if len(parameters['atommaskarray']) == 0:
      keystrokes_string += 'False\n' 
    else:    
      keystrokes_string += '%s\n' % str(parameters['atommaskarray'])
  if combination[0]:
    keystrokes_string += '%s\n' % str(parameters['sel_g'])
  if combination[0] or combination[1] == 2 or combination[2] == 3:
    keystrokes_string += '%s\n' % str(parameters['sel_t'])
    if parameters['sel_g'] or parameters['sel_t']:
      keystrokes_string += '%s\n' % str(parameters['eselect'])
  keystrokes_string += '%s\n' % str(parameters['laser'])  
  if parameters['laser']:
    keystrokes_string += '%s\n' % str(parameters['laserfile'])   
  keystrokes_string += '%s\n' % str(parameters['pysharc'])   
  keystrokes_string += '%s\t\t#Write output in NetCDF format\n' % str(parameters['netcdf'])
  keystrokes_string += '%s\n' % str(parameters['write_grad'])
  keystrokes_string += '%s\n' % str(parameters['write_NAC'])
  keystrokes_string += '%s\n' % str(parameters['write_property2d'])
  keystrokes_string += '%s\n' % str(parameters['write_property1d'])
  keystrokes_string += '%s\n' % str(parameters['write_overlap'])
  if len(parameters['stride']) == 1 and parameters['stride'][0] == 1:
    keystrokes_string += 'False\n'    
  else: 
    keystrokes_string += 'True\n'    
    stride_string = ''
    for entry in parameters['stride']:
      stride_string += '%s ' % str(entry) #TODO this is for sure not correct
    keystrokes_string += '%sstride\n' % stride_string 

  if parameters['here']:
    keystrokes_string += 'True\n'    
  else:
    keystrokes_string += 'False\n'    
    keystrokes_string += '%s\n'  % parameters['copydir']

  if parameters['qsub']:
    keystrokes_string += 'True\t\t#Generate submission script?\n'    
    keystrokes_string += '%s\t\t#Submission command\n' %  parameters['qsubcommand']
    keystrokes_string += '%s\n' %  parameters['proj']
  else:
    keystrokes_string += 'False\t\t#Generate submission script?\n'
  keystrokes_string += 'True\n'    #setup
  keystrokes_string += 'True\n'    #overwrite
   
  writefile('%s/KEYSTROKES.setup_traj_gym' % dir_string, keystrokes_string)

# ======================================================================= # 

def mod_molden(moldata, delete_modes, outstring):
  #delete_modes=[7]

  mod=False
  newmolden=[]
  j=0
  s=''
  for i in range(len(moldata)):
    line=moldata[i].split()
    if mod:
      j+=1
      if j in delete_modes:
        line=['0.0']
    if '[' in moldata[i]:
      mod=False
    if '[FREQ]' in line:
      mod=True
    for k in range(len(line)):
      s+='%s ' % line[k]
    s+='\n'
  writefile(outstring, s)

# ======================================================================= #

def make_directory(new_dir):
  '''Creates a directory'''

  if os.path.isfile(new_dir):
    print '\nWARNING: %s is a file!' % (new_dir)
    return -1
  if os.path.isdir(new_dir):
    if len(os.listdir(new_dir))==0:
      return 0
    else:
      print '\nWARNING: %s/ is not empty!' % (new_dir)
      if not 'overwrite' in globals():
        global overwrite
        overwrite = True

        #overwrite=question('Do you want to overwrite files in this and all following directories? ',bool,False)
      if overwrite:
        return 0
      else:
        return -1
  else:
    try:
      os.mkdir(new_dir)
    except OSError:
      print '\nWARNING: %s cannot be created!' % (new_dir)
      return -1
    return 0

# ======================================================================= #

def default_setup(INFOS, states):
  '''This function is almost identical to the default parameter question 
  part in setup_traj.py.'''
  
  #random number
  print '\nPlease enter a random number generator seed (type "!" to initialize the RNG from the system time).'
  while True:
    line = question('RNG Seed: ',str,'!',False)
    if line == '!':
      rng_seed = ''
      break
    try:
      rng_seed = int(line)
    except ValueError:
      print 'Please enter an integer or "!".'
      continue
    break
  print ''
  INFOS['rng'] = rng_seed

  # Simulation time
  print 'Please enter the total simulation time.'
  while True:
    num = question('Simulation time (fs):',float,[1000.])[0]
    if num <= 0:
      print 'Simulation time must be positive!'
      continue
    break
  INFOS['tmax'] = num

  # Timestep
  print '\nPlease enter the simulation timestep (0.5 fs recommended).'
  while True:
    dt = question('Simulation timestep (fs):',float,[0.5])[0]
    if dt <= 0:
      print 'Simulation timestep must be positive!'
      continue
    break
  INFOS['dtstep'] = dt
  print '\nSimulation will have %i timesteps.' % (num/dt+1)


  # number of substeps
  print '\nPlease enter the number of substeps for propagation (25 recommended).'
  while True:
    nsubstep = question('Nsubsteps:',int,[25])[0]
    if nsubstep <= 0:
      print 'Enter a positive integer!'
      continue
    break
  INFOS['nsubstep'] = nsubstep

  # whether to kill relaxed trajectories
  print '\nThe trajectories can be prematurely terminated after they run for a certain time in the lowest state. '
  INFOS['kill'] = question('Do you want to prematurely terminate trajectories?',bool,False)
  if INFOS['kill']:
    while True:
      tkill = question('Kill after (fs):',float,[10.])[0]
      if tkill <= 0:
        print 'Must be positive!'
        continue
      break
    INFOS['killafter'] = tkill
  print ''

  # Setup SOCs 
  diff_mults = 0
  for state_list in states:
    if state_list > 0:
      diff_mults += 1
  if diff_mults > 1:
    print 'Do you want to include spin-orbit couplings in the dynamics?\n'
    soc = question('Spin-Orbit calculation?',bool,True)
    if soc:
      print 'Will calculate spin-orbit matrix.'
  else:
    print 'Only singlets specified: not calculating spin-orbit matrix.'
    soc = False
  print ''

  INFOS['soc'] = soc  

  # Forced hops to lowest state
  print '\nDo you want to perform forced hops to the lowest state based on a energy gap criterion?'
  print '(Note that this ignores spin multiplicity)'
  INFOS['force_hops']=question('Forced hops to ground state?',bool, False)
  if INFOS['force_hops']:
    INFOS['force_hops_dE']=abs( question('Energy gap threshold for forced hops (eV):',float,[0.1])[0] )
  else:
    INFOS['force_hops_dE']=9999.

  # Scaling
  print '\nDo you want to scale the energies and gradients?'
  scal=question('Scaling?',bool,False)
  if scal:
    while True:
      fscal=question('Scaling factor (>0.0): ',float)[0]
      if fscal<=0:
        print 'Please enter a positive real number!'
        continue
      break
    INFOS['scaling']=fscal
  else:
    INFOS['scaling']=False


  # Damping
  print '\nDo you want to damp the dynamics (Kinetic energy is reduced at each timestep by a factor)?'
  damp=question('Damping?',bool,False)
  if damp:
    while True:
      fdamp=question('Scaling factor (0-1): ',float)[0]
      if not 0<=fdamp<=1:
        print 'Please enter a real number 0<=r<=1!'
        continue
      break
    INFOS['damping']=fdamp
  else:
    INFOS['damping']=False


  # atommask
  INFOS['atommaskarray']=[]
#  if (INFOS['decoherence'][0]=='edc') or (INFOS['ekincorrect']==2) or (INFOS['reflect']==2):
  print '\nDo you want to use an atom mask for velocity rescaling or decoherence?'
  if question('Atom masking?',bool,False):
    print '\nPlease enter all atom indices (start counting at 1) of the atoms which should be masked. \nRemember that you can also enter ranges (e.g., "-1~-3  5  11~21").'
    arr=question('Masked atoms:',int,ranges=True)
    for i in arr:
#      if 1<=i<=INFOS['natom']:
      INFOS['atommaskarray'].append(i)

  # selection of gradients (only for SHARC) and NACs (only if NAC=ddr)
#  print '\n'+centerstring('Selection of Gradients and NACs',60,'-')+'\n'
  print '''In order to speed up calculations, SHARC is able to select which gradients and NAC vectors it has to calculate at a certain timestep. The selection is based on the energy difference between the state under consideration and the classical occupied state.
'''
#  if INFOS['surf']=='diagonal':
#    if INFOS['soc']:
  sel_g=question('Select gradients?',bool,False)
#    else:
#      sel_g=True
#  else:
#    sel_g=False
  INFOS['sel_g']=sel_g
#  if Couplings[INFOS['coupling']]['name']=='ddr' or INFOS['gradcorrect'] or EkinCorrect[INFOS['ekincorrect']]['name']=='parallel_nac':
  sel_t=question('Select non-adiabatic couplings?',bool,False)
#  else:
#    sel_t=False
  INFOS['sel_t']=sel_t
  if sel_g or sel_t:
#    if not sel_t and not INFOS['soc']:
#      INFOS['eselect']=0.001
#      print '\nSHARC dynamics without SOC and NAC: setting minimal selection threshold.'
#    else:
    print '\nPlease enter the energy difference threshold for the selection of gradients and non-adiabatic couplings (in eV). (0.5 eV recommended, or even larger if SOC is strong in this system.)'
    eselect=question('Selection threshold (eV):',float,[0.5])[0]
    INFOS['eselect']=abs(eselect)


  # Laser file
#  print '\n\n'+centerstring('Laser file',60,'-')+'\n'
  INFOS['laser']=question('Do you want to include a laser field in the simulation?',bool,False)
  if INFOS['laser']:
    print '''Please specify the file containing the complete laser field. The timestep in the file and the length of the file must fit to the simulation time, time step and number of substeps given above.

Laser files can be created using $SHARC/laser.x
'''
    if os.path.isfile('laser'): 
      if check_laserfile('laser',INFOS['tmax']/INFOS['dtstep']*INFOS['nsubstep']+1,INFOS['dtstep']/INFOS['nsubstep']):
        print 'Valid laser file "laser" detected. '
        usethisone=question('Use this laser file?',bool,True)
        if usethisone:
          INFOS['laserfile']='%s/laser' % os.getcwd()
    if not 'laserfile' in INFOS:
      while True:
        filename=question('Laser filename:',str)
        if not os.path.isfile(filename):
          print 'File %s does not exist!' % (filename)
          continue
        if check_laserfile(filename,INFOS['tmax']/INFOS['dtstep']*INFOS['nsubstep']+1,INFOS['dtstep']/INFOS['nsubstep']):
          break
      INFOS['laserfile']=os.path.abspath(filename)
    # only the analytical interface can do dipole gradients
#    if 'dipolegrad' in Interfaces[INFOS['interface']]['features']:
#      INFOS['dipolegrad']=question('Do you want to use dipole moment gradients?',bool,False)
#    else:
#      INFOS['dipolegrad']=False
#    print ''
#  else:
#    INFOS['dipolegrad']=False
#  if INFOS['dipolegrad']:
#    INFOS['needed'].extend(Interfaces[INFOS['interface']]['features']['dipolegrad'])



  # Setup Dyson computation
#  INFOS['ion']=False
#  if 'dyson' in Interfaces[INFOS['interface']]['features']:
#    n=[0,0]
#    for i,j in enumerate(INFOS['states']):
#      n[i%2]+=j
#    if n[0]>=1 and n[1]>=1:
#      print '\n'+centerstring('Ionization probability by Dyson norms',60,'-')+'\n'
#      print 'Do you want to compute Dyson norms between neutral and ionic states?'
#      INFOS['ion']=question('Dyson norms?',bool,False)
#      if INFOS['ion']:
#        INFOS['needed'].extend(Interfaces[INFOS['interface']]['features']['dyson'])


  # Setup theodore
#  if 'theodore' in Interfaces[INFOS['interface']]['features']:
#    print '\n'+centerstring('TheoDORE wave function analysis',60,'-')+'\n'
#    print 'Do you want to run TheoDORE to obtain one-electron descriptors for the electronic wave functions?'
#    INFOS['theodore']=question('TheoDORE?',bool,False)
#   if INFOS['theodore']:
#      INFOS['needed'].extend(Interfaces[INFOS['interface']]['features']['theodore'])







  # PYSHARC
#  if Interfaces[ INFOS['interface']]['pysharc']:
#    string='\n  '+'='*80+'\n'
#    string+='||'+centerstring('PYSHARC',80)+'||\n'
#    string+='  '+'='*80+'\n'
#    print string
#    print '\nThe chosen interface can be run very efficiently with PYSHARC.'
  print 'PYSHARC runs the SHARC dynamics directly within Python (with C and Fortran extension)'
  print 'with minimal file I/O for maximum performance.'
  INFOS['pysharc']=question('Setup for PYSHARC?',bool,True)
#  else:
#    INFOS['pysharc']=False

  # Dynamics options
#  string='\n  '+'='*80+'\n'
#  string+='||'+centerstring('Content of output.dat files',80)+'||\n'
#  string+='  '+'='*80+'\n'
#  print string

  # NetCDF
  print '\nSHARC or PYSHARC can produce output in ASCII format (all features supported currently)'
  print 'or in NetCDF format (more efficient file I/O, some features currently not supported).'
  INFOS['netcdf']=question('Write output in NetCDF format?',bool,INFOS['pysharc'])


  # options for writing to output.dat
  print '\nDo you want to write the gradients to the output.dat file ?'
  write_grad=question('Write gradients?',bool,False)
  if write_grad:
    INFOS['write_grad']=True
  else:
    INFOS['write_grad']=False

  print '\nDo you want to write the non-adiabatic couplings (NACs) to the output.dat file ?'
  write_NAC=question('Write NACs?',bool,False)
  if write_NAC:
    INFOS['write_NAC']=True
  else:
    INFOS['write_NAC']=False


  print '\nDo you want to write property matrices to the output.dat file  (e.g., Dyson norms)?'
  if 'ion' in INFOS and INFOS['ion']:
    INFOS['write_property2d']=question('Write property matrices?',bool,True)
  else:
    INFOS['write_property2d']=question('Write property matrices?',bool,False)


  print '\nDo you want to write property vectors to the output.dat file  (e.g., TheoDORE results)?'
  if 'theodore' in INFOS and INFOS['theodore']:
    INFOS['write_property1d']=question('Write property vectors?',bool,True)
  else:
    INFOS['write_property1d']=question('Write property vectors?',bool,False)


  print '\nDo you want to write the overlap matrix to the output.dat file ?'
  INFOS['write_overlap']=question('Write overlap matrix?',bool, True )


  print '\nDo you want to modify the output.dat writing stride?'
  stride=question('Modify stride?',bool,False)
  if stride:
    INFOS['stride']=[]
    stride=question('Enter the  *INITIAL*   output stride (e.g., "1"=write every step)',int,[1])
    INFOS['stride'].extend(stride)
    stride=question('Enter the *SUBSEQUENT* output stride (e.g., "10 2"=write every second step starting at step 10)',int,[0,1])
    INFOS['stride'].extend(stride)
    stride=question('Enter the   *FINAL*    output stride (e.g., "100 10"=write every tenth step starting at step 100)',int,[0,1])
    INFOS['stride'].extend(stride)
  else:
    INFOS['stride']=[1]

  print '''This script can generate the run scripts for each initial condition in two modes:

  - In mode 1, the calculation is run in subdirectories of the current directory.

  - In mode 2, the input files are transferred to another directory (e.g. a local scratch directory), the calculation is run there, results are copied back and the temporary directory is deleted. Note that this temporary directory is not the same as the "scratchdir" employed by the interfaces.

Note that in any case this script will create the input subdirectories in the current working directory. 
'''
  print 'In case of mode 1, the calculations will be run in the respective directory\n' 
  here=question('Use mode 1 (i.e., calculate here)?',bool,True)
  if here:
    INFOS['here']=True
  #  INFOS['copydir']=INFOS['cwd']
  else:
    INFOS['here']=False
    print '\nWhere do you want to perform the calculations? Note that this script cannot check whether the path is valid.'
    INFOS['copydir']=question('Run directory?',str)
  print ''

 # print centerstring('Submission script',60,'-')+'\n'
  print '''During the setup, a script for running all initial conditions sequentially in batch mode is generated. Additionally, a queue submission script can be generated for all initial conditions.
'''
  qsub=question('Generate submission script?',bool,False)
  if not qsub:
    INFOS['qsub']=False
  else:
    INFOS['qsub']=True
    print '\nPlease enter a queue submission command, including possibly options to the queueing system,\ne.g. for SGE: "qsub -q queue.q -S /bin/bash -cwd" (Do not type quotes!).'
    INFOS['qsubcommand']=question('Submission command?',str,None,False)
    INFOS['proj']=question('Project Name:',str,None,False)

  print ''


  return INFOS

# ======================================================================= #

def check_laserfile(filename,nsteps,dt):
  try:
    f=open(filename)
    data=f.readlines()
    f.close()
  except IOError:
    print 'Could not open laser file %s' % (filename)
    return False
  n=0
  for line in data:
    if len(line.split())>=8:
      n+=1
    else:
      break
  if n<nsteps:
    print 'File %s has only %i timesteps, %i steps needed!' % (filename,n,nsteps)
    return False
  for i in range(int(nsteps)-1):
    t0=float(data[i].split()[0])
    t1=float(data[i+1].split()[0])
    if abs(abs(t1-t0)-dt)>1e-6:
      print 'Time step wrong in file %s at line %i.' % (filename,i+1)
      return False
  return True

# ======================================================================= #

def parameter_selection(states):
  '''All surface hopping parameters for the trajectories are obtained and stored 
  as a dictionary, similar to the corresponding INFOS file using the same set of 
  keys. After setting up all non-screened parameters, all parameters that need to 
  be screened are asked. When adding a new to-be-screened parameter, take care to
  also change the write_keystrokes_traj function as well as the read out of the
  SHARC_gym_analysis.py script.'''
  
  parameters = {}

  #first obtain all non-screened parameters
  parameters = default_setup(parameters, states)

  print '\nFrom here on, all the different surface hopping parameters that can be screened will be shown.'
  print 'In case the given property should not be screened, a new prompt for the default parameter will be asked.\n'

  while True:  
    results = []

    #SHARC/MCH -> if SHARC extra line after coupling
    diff_mults = 0
    for state_list in states:
      if state_list > 0:
        diff_mults += 1
    if diff_mults > 1:
    # SHARC or FISH
      print '\nDo you want to perform the dynamics in the diagonal representation (SHARC dynamics) or in the MCH representation (regular surface hopping)?'
      screen = question('Do you want to screen this property?',bool,False)
      if screen:
        parameters['surf'] = [True, False]
      else:
        surf=question('SHARC dynamics?',bool,True)
        parameters['surf'] = [[False, True][surf]]
    else:
      parameters['surf'] = [False]
    results.append(parameters['surf'])

    # Coupling
    print '\nPlease choose the quantities to describe non-adiabatic effects between the states:'
    for i in Couplings:
      print '%i\t%s' % (i,
                          Couplings[i]['description']
                          )
    #print ''
    print'\nTo screen multiple couplings, add all desired numbers separated by spaces.'
    while True:
      numbers = question('Coupling number:',int,[3])
      for num in numbers:
        if num not in Couplings or num == 1:
          break
      else:
        break
    if isinstance(numbers, int):
      numbers = [numbers]
    parameters['coupling']=numbers
    print numbers
    results.append(parameters['coupling'])

    #ekincorrect
    print '\nDuring a surface hop, the kinetic energy has to be modified in order to conserve total energy. There are several options to that:'
    for i in EkinCorrect:
      print '%i\t%s' % (i,
                          EkinCorrect[i]['description']
                          )
    print'\nTo screen multiple energy adjustments, add all desired numbers separated by spaces.'
  #  for i in EkinCorrect:
  #    recommended=len(EkinCorrect[i]['required'])==0  
    while True:
      numbers=question('EkinCorrect:',int,[2])
      for ekinc in numbers:
        if ekinc not in EkinCorrect:
          break
      else:
          break
    if isinstance(numbers, int):
      numbers = [numbers]
    parameters['ekincorrect'] = numbers
    results.append(parameters['ekincorrect'])

    # reflect
    print '\nIf a surface hop is refused (frustrated) due to insufficient energy, the velocity can either be left unchanged or reflected:'
    for i in EkinCorrect:
      print '%i\t%s' % (i,
                          EkinCorrect[i]['description_refl']
                          )
    #print ''
    print'\nTo screen multiple reflection schemes, add all desired numbers separated by spaces.'
    while True:
      numbers = question('Reflect frustrated:',int,[1])
      for num in numbers:
        if num not in EkinCorrect:
          break
      else:
        break
    if isinstance(numbers, int):
      numbers = [numbers]
    parameters['reflect']=numbers
    print numbers
    results.append(parameters['reflect'])

    # decoherence
    print '\nPlease choose a decoherence correction for the simulation:'
    for i in Decoherences:
      print '%i\t%s' % (i,
                          Decoherences[i]['description']
                          )
    #print ''
    print'\nTo screen multiple decoherence schemes, add all desired numbers separated by spaces.'
    while True:
      numbers = question('Decoherence scheme:',int,[2])
      for num in numbers:
        if num not in Decoherences:
          break
      else:
        break
    if isinstance(numbers, int):
      numbers = [numbers]
    parameters['decoherence']=numbers
    results.append(parameters['decoherence'])
    print numbers

    # surface hopping scheme
    print '\nPlease choose a surface hopping scheme for the simulation:'
    for i in HoppingSchemes:
      print '%i\t%s' % (i,
                          HoppingSchemes[i]['description']
                          )
    #print ''
    print'\nTo screen multiple decoherence schemes, add all desired numbers separated by spaces.'
    while True:
      numbers = question('Surface hopping scheme:',int,[2])
      for num in numbers:
        if num not in HoppingSchemes:
          break
      else:
        break
    if isinstance(numbers, int):
      numbers = [numbers]
    parameters['hopping']=numbers
    results.append(parameters['hopping'])  
    #print numbers
    #print results
    #this generates all possible combinations from taking a single element from each list
    #the order in each generated sub-tuple  corresponds to the order of the parent lists
    # this means, each tuple is ordered [surf,coupling,ekinadjust,reflect,decoherence,hopping]
    parameters['combinations'] = [x for x in itertools.product(*results)]
    print 'The selection of screened parameters results in %i combinations.' % len(parameters['combinations'])
    if question('Do you want to proceed with this setup?', bool, True):
      break
    elif not question('Do you want to select a new set of parameters to screen?', bool, True):
      print 'Ending now...'
      sys.exit()
  return parameters

# ======================================================================= #

def main():

  #the keystrokes file can be used to repeat the sequence of chosen options 
  #for a repeated run of the gym via "SHARC_gym.py < KEYSTROKES.SHARC_gym"
  open_keystrokes()


  #set up either Hamiltonian or Parameter loop
  print '\nPlease choose a method to analyze the chosen property:' 
  cando=list(Loops)
  for i in Loops:
    print '%i\t%s' % (i, Loops[i]['description'])
  while True:
    current_loop = question('Choose a mode to analyze the chosen property:',int)[0]
    if current_loop in Loops and current_loop in cando:
      break
    else:
      print 'Please input one of the following: %s!' % ([i for i in cando])

  #get input files
  input_file = 'sharc_gym.in'

  lvc_file = ''
  if os.path.isfile('LVC.template'):
    print 'File "LVC.template" detected. '
    usethisone=question('Use this template file?',bool,True)
    if usethisone:
      lvc_file = '%s/LVC.template' % os.getcwd()
  if lvc_file == '':
    while True:
      filename=question('Template filename:',str)
      if not os.path.isfile(filename):
        print 'File %s does not exist!' % (filename)
        continue
      break
    filename = os.path.expanduser(os.path.expandvars(filename))
    filename = os.path.abspath(filename)
    lvc_file = filename
  print 'Using %s as base LVC.template' % lvc_file

  sharc_gym_input = read_input(input_file)
  ref_hamiltonian = read_hamiltonian(lvc_file)
  freq = readfile(sharc_gym_input['molden'][0])

  #set up loops and generate all subdirectories
  if current_loop == 1:
    final_modes = mode_selection(sharc_gym_input, ref_hamiltonian)
    final_states = state_selection(sharc_gym_input, ref_hamiltonian)
    parameters = {}
  elif current_loop == 2:
    final_modes = ref_hamiltonian['used_modes']
    state_list = [ [] for x in range(len(ref_hamiltonian['states'])) ]
    for x in range(len(ref_hamiltonian['states'])):
      for k in range(int(ref_hamiltonian['states'][x])):
        state_list[x].append(k+1)    
    final_states = state_list  
    parameters = parameter_selection(ref_hamiltonian['states'])
  setup_dynamics(ref_hamiltonian, freq, final_modes, final_states, parameters, current_loop)
  close_keystrokes()



main()

