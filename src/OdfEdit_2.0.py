#-------------------------------------------------------------------------------
# Name:        OdfEdit
# Purpose:     Application helping to edit an organ definition file (ODF) in plain text
#              The ODF can be used in the GrandOrgue application
#              Implemented with Python 3
#              Tested in Windows 10 and Ubuntu 21.10
#              It is contains 4 classes :
#                   C_ODF to manage and check the ODF data
#                   C_HW2GO to manage the convertion from a Hauptwerk ODF to a GrandOrgue ODF
#                   C_GUI to manage the graphical user interface of this application
#                   CreateToolTip to display a tool tip on a GUI widget
# Author:      Eric Turpault (France, Châtellerault)
# Copyright:   open source
# Licence:     free to modify, please share the modification with the author
#
# The considered GrandOrgue ODF syntax is :
#    [object_UID]
#    ; comment line, empty lines are ignored
#    ; object_UID can contain only alphanumeric characters
#    attribute1=value1
#    attribute2=value2
#    ; attribute can contain only alphanumeric or '_' characters
#
# The new panel format is detected if the Panel000 object is present and contains the attribute NumberOfGUIElements
#
# Versions history :
#   v1.0 - 15 April 2022 - initial version
#   v1.1 - 16 April 2022 - minor changes to be Linux compatible, minor GUI fixes
#   v1.2 - 27 April 2022 - some GUI behavior improvements, minor improvements in the help and the objects checks
#   v1.3 - 19 May   2022 - data management improvement, change in the way to define the parent-child relations between the objects,
#                          completed some attributes values maximum check, added a tab to search a string in the whole ODF
#   v2.0 - 23 Dec.  2022 - fix made in the function check_object_Manual around the key_type checks
#                          fix made in the function check_attribute_value to not change out of range integer value and better check HTML color code
#                          use the PIL library instead of Tk to check the sample set images sizes
#                          first implementation of the Hauptwerk to GrandOrgue ODF conversion feature
#-------------------------------------------------------------------------------

MAIN_WINDOW_TITLE = "OdfEdit - v2.0"

import os
import inspect
from tkinter import *
from tkinter import filedialog as fd
from tkinter import messagebox, ttk
import tkinter.font as tkf

from PIL import Image  ## install with : pip install pillow
from lxml import etree ## install instruction : https://stackoverflow.com/a/40202702

DISP_HW_OBJECTS_TREE = True # True or False, to display or not a notebook tab with Hauptwerk objects tree if a Hauptwerk ODF is loaded

HW_CONV_MSG = """An ODF will be built in order to permit to use the selected Hauptwerk sample set with the GrandOrgue application. None file of the Hauptwerk sample set will be modified.
ATTENTION :
- Please do this operation only with a free Hauptwerk sample set or a not-free sample set that you have duly paid for, and if the editor of this sample set does not preclude its use outside Hauptwerk application.
- Don't expect to have necessarily with GrandOrgue the sound quality and all control possibilities that this sample set can provide with Hauptwerk.
"""

IDX_OBJ_NAME = 0 # index in the objects dictionnary entry list of the object name
IDX_OBJ_PAR = 1  # index in the objects dictionnary entry list of the object parents
IDX_OBJ_CHI = 2  # index in the objects dictionnary entry list of the object children
IDX_OBJ_LINE = 3 # index in the objects dictionnary entry list of the object ID line number in the ODF lines list
ENCODING_ISO_8859_1 = 'ISO-8859-1'  # one of the two supported encoding type for an ODF
ENCODING_UTF8_BOM = 'utf_8_sig'     # one of the two supported encoding type for an ODF
ALLOWED_CHARS_4_FIELDS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'  # characters allowed in a attribute name

# data types used in the attributes of the objects, used in the check object/attribute functions
ATTR_TYPE_INTEGER = 1
ATTR_TYPE_FLOAT = 2
ATTR_TYPE_BOOLEAN = 3
ATTR_TYPE_STRING = 4
ATTR_TYPE_COLOR = 5            # used in Button, Enclosure, Label, Panel
ATTR_TYPE_FONT_SIZE = 6        # used in Button, Enclosure, Label
ATTR_TYPE_PANEL_SIZE = 7       # used in Panel
ATTR_TYPE_COUPLER_TYPE = 8     # used in Coupler
ATTR_TYPE_ELEMENT_TYPE = 9     # used in Panel Element
ATTR_TYPE_TREMULANT_TYPE = 10  # used in Tremulant
ATTR_TYPE_PISTON_TYPE = 11     # used in Piston
ATTR_TYPE_DRAWSTOP_FCT = 12    # used in DrawStop
ATTR_TYPE_FILE_NAME = 13       # used in many objects for bitmap or wav files
ATTR_TYPE_OBJECT_REF = 14      # used in many objects to make a reference to another object ID
ATTR_TYPE_PIPE_WAVE = 15       # used in Rank

# constants to identify a link between objects
TO_PARENT = False
TO_CHILD = True

#-------------------------------------------------------------------------------------------------
class C_ODF:
    #--- class to store and manage the GO ODF data

    odf_file_name = ""      # name of the ODF file which the data have been loaded in odf_lines_list
    odf_file_encoding = ""  # encoding type of the loaded ODF
    odf_lines_list = []     # list containing the lines coming from the loaded ODF
    odf_objects_dic = {}    # dictionnary having as keys objects UID (unique identifier) of the ODF (sorted). Each key has as value a list with the following items :
                            #   item 1 (index IDX_OBJ_NAME) : object names (string)
                            #   item 2 (index IDX_OBJ_PAR)  : object parents (list of objects UID)
                            #   item 3 (index IDX_OBJ_CHI)  : object children (list of objects UID)
                            #   item 4 (index IDX_OBJ_LINE) : number of the line in the ODF lines list where is located the object_UID of the key (integer)
                            # summarized like this : ['object_names', ['parent1_obj_UID', 'parent2_obj_UID',...], ['child1_obj_UID', 'child2_obj_UID',...], line_number]
    new_panel_format = False  # flag indicating if the loaded ODF uses the new panel format or not
    check_files_names = ""  # flag storing the choice of the user to check or not the files names in the ODF ('' for not defined, False, True)
    check_nb_attr = 0       # number of attributes checked during the checking operation
    events_log_list = []    # list of events logs (errors or messages resulting from file operation or syntax check)

    #-------------------------------------------------------------------------------------------------
    def odf_lines_load(self, file_name_str):
        #--- load in odf_lines_list the content of the given ODF
        #--- returns True/False whether the file has been loaded correctly or not

        # open the given ODF in read mode, and check its encoding format
        try:
            f = open(file_name_str, mode='r', encoding=ENCODING_ISO_8859_1)
        except OSError as err:
            # it has not be possible to open the file
            self.events_log_add(f"Cannot open the file. {err}")
            valid_odf_file = False
        else:
            if f.readline(3) == "ï»¿":  # UTF-8 BOM file encoding header
                # close the file
                f.close()
                # reopen the file with the proper encoding format
                f = open(file_name_str, mode='r', encoding=ENCODING_UTF8_BOM)
                self.odf_file_encoding = ENCODING_UTF8_BOM
            else:
                f.seek(0)  # reset the position of the cursor at the beginning of the file
                self.odf_file_encoding = ENCODING_ISO_8859_1
            # store the name of the ODF
            self.odf_file_name = file_name_str
            valid_odf_file = True

            # clear the lists/dict content
            self.odf_lines_list.clear()
            self.odf_objects_dic.clear()

            # load in the ODF lines list the content of the given ODF
            object_attr_nb_int = 0
            object_UID = ''
            object_UID_list = []
            for line in f:
                if line[-1:] == '\n': line = line[:-1]  # remove the ending \n characters if any
                line = line.rstrip()  # remove the trailing whitespaces if any

                if self.is_line_with_object_UID(line): # line with an object ID
                    object_UID = line[1:-1] # remove the brackets in first and last characters to get the object ID

                    while object_UID in object_UID_list:
                        # there is already an object ID with the same name in the list : add _ at end of the ID until the ID is unique
                        # this is done in order to avoid duplicate IDs in the objects list, the user will have to fix it
                        self.events_log_add(f"Another occurence of the object {object_UID} is present, it has been renamed in {object_UID}_")
                        object_UID += '_'
                    line = '[' + object_UID + ']'
                    # add the object ID to the objects list
                    object_UID_list.append(object_UID)
                elif self.is_line_with_attribute(line): # line with an attribute
                    object_attr_nb_int += 1 # increment the counter counting the number of defined attributes

                # add the line to the ODF lines list
                self.odf_lines_list.append(line)

            # close the ODF
            f.close()

            # update the objects dictionnary from the ODF lines list content
            self.objects_dic_update()
            # update the panel format flag from the ODF lines list content
            self.check_odf_panel_format()
            # reset the check files names flag
            self.check_files_names = ''

            self.events_log_add(f'GrandOrgue ODF loaded "{file_name_str}"')
            self.events_log_add(f'{str(object_attr_nb_int)} attributes among {str(len(object_UID_list))} objects, file encoding {self.odf_file_encoding}')
            if self.new_panel_format:
                self.events_log_add('New panel format')
            else:
                self.events_log_add('Old panel format')

        return valid_odf_file

    #-------------------------------------------------------------------------------------------------
    def odf_lines_save(self, file_name_str):
        #--- save odf_lines_list in the given ODF
        #--- if no file name is given, the saving is done in the already loaded ODF file
        #--- returns True/False whether the writting in file has been done correctly or not

        if len(self.odf_lines_list) == 0:
            # the ODF lines list is empty, there are no data to save
            self.events_log_add(f"None data to save in the file {file_name_str}")
            file_saved = False
        elif file_name_str == '' and self.odf_file_name == '':
            # no file name known, so no possibility to make the save operation
            file_saved = False
        else:
            # open the given ODF in write mode
            if file_name_str == '':
                # no given file name, make the saving in the already loaded ODF
                file_name_str = self.odf_file_name

            if self.odf_file_encoding == '':
                self.odf_file_encoding = ENCODING_UTF8_BOM

            # check if the file name has an extension, if not add the .organ extension
            if file_name_str[-6:] != '.organ':
                file_name_str += '.organ'

            try:
                f = open(file_name_str, mode='w', encoding=self.odf_file_encoding)
            except OSError as err:
                self.events_log_add(f"Cannot write in the file. {err}")
                file_saved = False
            else:
                # write odf_lines_list in the ODF, removing the consecutive empty lines, and ensuring an empty line before each object ID
                prev_line = ''
                for line in self.odf_lines_list:
                    if line[:1] == '[' and prev_line != '':
                        # object ID line without empty line before : add an empty line
                        f.write('\n')
                    if not (line == '' and prev_line == ''):
                        # not empy line following a previous empty line (to remove consecutive empty lines)
                        # write the line in the file
                        f.write(line + '\n')
                    prev_line = line
                f.close()
                file_saved = True

                # store the name of the ODF file
                self.odf_file_name = file_name_str

                self.events_log_add(f"Data saved in file '{file_name_str}' with encoding {self.odf_file_encoding}")

        return file_saved

    #-------------------------------------------------------------------------------------------------
    def odf_reset_all_data(self):
        #--- reset all the data of the class

        self.odf_file_name = ''
        self.odf_file_encoding = ENCODING_ISO_8859_1
        self.odf_lines_list.clear()
        self.odf_objects_dic.clear()
        self.events_log_clear()
        self.new_panel_format = False

    #-------------------------------------------------------------------------------------------------
    def events_log_add(self, log_string):
        #--- add the given string to the events log list

        self.events_log_list.append(log_string)

    #-------------------------------------------------------------------------------------------------
    def events_log_clear(self):
        #--- clear the events log list

        self.events_log_list.clear()

    #-------------------------------------------------------------------------------------------------
    def objects_dic_update(self):
        #--- (re)build the ODF objects dictionnary from the ODF lines list

        # parse the ODF lines list to recover all the present objects IDs
        object_UID_list = []
        for line in self.odf_lines_list:
            if self.is_line_with_object_UID(line):
                # line with an object ID : add it in the objects ID list without the surrounding brackets
                object_UID_list.append(line[1:-1])
        # sort the objects ID list
        object_UID_list.sort()

        # initialize the ODF objects dictionnary using the items of the objects ID list as the keys of the dictionnary
        self.odf_objects_dic.clear()
        for object_UID in object_UID_list:
            self.odf_objects_dic[object_UID] = ['', [], [], -1]  # set the format of each entry of the dictionnary

        object_UID = ''  # ID of the object for which we are parsing the attributes

        # parse the ODF lines list to fill the dictionnary values
        for index, line in enumerate(self.odf_lines_list):

            if self.is_line_with_object_UID(line):
                # line with an object ID
                # recover the object ID without the surrounding brackets
                object_UID = line[1:-1]
                object_UID_str_len = len(object_UID)

                # write in the dictionnary entry of this object ID the index of the line in the ODF lines list
                self.odf_objects_dic[object_UID][IDX_OBJ_LINE] = index

                if object_UID.startswith(('General', 'Manual', 'WindchestGroup', 'Image', 'Label', 'ReversiblePiston', 'SetterElement')):
                    # General999, Manual999, WindchestGroup999, ... object
                    # add a link between 'Organ' (parent) and this object (child)
                    self.objects_dic_append_child('Organ', object_UID)
                elif object_UID.startswith('Panel'):
                    if object_UID_str_len == 8:
                        # Panel999 object
                        # add a link between 'Organ' (parent) and this Panel999 (child)
                        self.objects_dic_append_child('Organ', object_UID)
                    elif object_UID_str_len > 8:
                        # Panel999NNNNN999 object
                        # add a link between Panel999 (parent) and this Panel999NNNNN999 (child)
                        self.objects_dic_append_child(object_UID[0:8], object_UID)

            elif self.is_line_with_attribute(line):
                # line which contains an attribute
                # recover the attribute name and its value (around the equal character)
                (attr_name_str, attr_value_str) = line.split("=", 1)

                if attr_name_str[-3:].isdigit() and attr_value_str.isdigit():
                    # attribute which ends with 3 digits (like Coupler999) : it contains in its value the reference to another object
                    # add a link between the object ID to which belongs this attribute (parent) and the referenced other object ID (child)
                    self.objects_dic_append_child(object_UID, attr_name_str[:-3] + attr_value_str.zfill(3))
                elif attr_name_str == 'WindchestGroup' and attr_value_str.isdigit():
                    # attribute WindchestGroup : it contains in its value the reference to a WindchestGroup
                    # add a link between the referenced WindchestGroup (parent) and the object ID to which belongs this attribute (child)
                    self.objects_dic_append_child(attr_name_str + attr_value_str.zfill(3), object_UID)
                elif object_UID[8:15] == 'Element' and attr_name_str in ('Coupler', 'Divisional', 'DivisionalCoupler', 'Enclosure', 'Stop', 'Switch', 'Tremulant'):
                    # panel element of the new panel format with a reference to an object of the main panel
                    # add a link between the object_UID (parent) and the referenced object (child)
                    self.objects_dic_append_child(object_UID, attr_name_str + attr_value_str.zfill(3))

                # recover in the attributes a name for the current object
                if (attr_name_str in ["Name", "ChurchName", "Type", "Image"] or attr_name_str[-4:] == "Text") and attr_value_str != "":
                    # the attribute is Name / ChurchName / Type / Image / ...Text and has a value defined
                    if attr_name_str == "Image":
                        # image attribute, the value is the path of the image : keep from the image path only the file name
                        attr_value_str = os.path.basename(attr_value_str)
                    # add the attribute value as name of this object
                    self.objects_dic_append_name(object_UID, attr_value_str)

        # sort the parents / children lists in each entry of the dictionnary
        for object_UID in self.odf_objects_dic:
            self.odf_objects_dic[object_UID][IDX_OBJ_PAR].sort()
            self.odf_objects_dic[object_UID][IDX_OBJ_CHI].sort()

##        self.objects_dic_save2file('objects_list_dic.txt')

    #-------------------------------------------------------------------------------------------------
    def objects_dic_append_name(self, object_UID, name_to_add):
        #--- append in the objects dictionnary a name for the given object ID

        if object_UID in self.odf_objects_dic:
            # add the given name to the name attribute of the entry of this object
            if len(self.odf_objects_dic[object_UID][IDX_OBJ_NAME]) == 0:
                self.odf_objects_dic[object_UID][IDX_OBJ_NAME] = name_to_add
            else:
                self.odf_objects_dic[object_UID][IDX_OBJ_NAME] = self.odf_objects_dic[object_UID][IDX_OBJ_NAME] + ' | ' + name_to_add
        else:
            pass  # do nothing if the object ID is not present in the dictionnary, this should never happen because the name to add comes from this object

    #-------------------------------------------------------------------------------------------------
    def objects_dic_append_child(self, parent_object_UID, child_object_UID):
        #--- append in the objects dictionnary a link between the given parent / child objects

        if parent_object_UID in self.odf_objects_dic and child_object_UID in self.odf_objects_dic:
            # append the child object_UID to its parent properties
            self.odf_objects_dic[parent_object_UID][IDX_OBJ_CHI].append(child_object_UID)
            # append the parent object_UID to its child properties
            self.odf_objects_dic[child_object_UID][IDX_OBJ_PAR].append(parent_object_UID)

    #-------------------------------------------------------------------------------------------------
    def objects_dic_save2file(self, file_name_str):
        #--- save the ODF objects dictionnary into the given file (for debug purpose)

        with open(file_name_str, 'w') as f:
            # write the dictionnary
            f.write('object ID : [object name, parents, children]\n')
            f.write('----------------------------------------\n')
            for obj_UID, obj_prop_list in self.odf_objects_dic.items():
                f.write('%s:%s\n' % (obj_UID, obj_prop_list))

    #-------------------------------------------------------------------------------------------------
    def objects_type_count(self, HW_object_type_str):
        #--- count the number of objects having the given object type (Manual, Enclosure, ...) in the objects dictionnary with a 3-digits ending index higher than 1
        #--- returns the number of found objects

        counter = 0
        for object_UID in self.odf_objects_dic:
            if object_UID[:-3] == HW_object_type_str and object_UID[-3:].isdigit():
                if int(object_UID[-3:]) > 0 :
                    counter += 1
                elif HW_object_type_str not in ('Panel', 'Manual'):
                    self.events_log_add(f"Error : the object identifier {object_UID} cannot have the index 000")
        return counter

    #-------------------------------------------------------------------------------------------------
    def object_get_lines_range(self, object_UID):
        #--- return the indexes range of the object section (ID + attributes) in the ODF lines list
        #--- returns the range (0, 0) if the object ID has not been found

        if object_UID == 'Header':
            # the header of the odf_lines_list
            # set the index to start the search from the beginning of the ODF lines list
            line_idx_first = line_idx_last = 0
        elif object_UID in self.odf_objects_dic:
            # recover in the dictionnary the index of the line where starts the given object ID
            line_idx_first = self.odf_objects_dic[object_UID][IDX_OBJ_LINE]
            # set the index to start the search from the line after the object ID
            line_idx_last = line_idx_first + 1
        else:
            # return a void range since the object_UID is not in the dictionnary
            return (0,0)

        # search for the start of the next object, or the end of odf_lines_list
        while line_idx_last < len(self.odf_lines_list) and not(self.is_line_with_object_UID(self.odf_lines_list[line_idx_last])):
            # no list end and no next object ID reached
            line_idx_last += 1

        if line_idx_last == line_idx_first:
            # no range found
            return (0,0)
        else:
            # range found inside odf_lines_list
            return (line_idx_first, line_idx_last)

    #-------------------------------------------------------------------------------------------------
    def object_get_data_list(self, object_UID):
        #--- return from the ODF lines list the object section lines (object ID + attributes) of the given object ID
        #--- if the object has not be found, return an empty list

        # get the lines range of the object in odf_lines_list
        obj_range = self.object_get_lines_range(object_UID)

        if obj_range != (0, 0):
            return self.odf_lines_list[obj_range[0]:obj_range[1]]
        else:
            return []

    #-------------------------------------------------------------------------------------------------
    def object_get_attribute_value(self, object_UID_or_list, attribute, is_list_sorted = False):
        #--- returns the value (string) of the given attribute defined in the given object ID section of the ODF lines list
        #---   or defined in the given object lines list (which can be sorted, to accelerate the search)
        #--- returns a tuple (attribute value if found else '', index of the attribute in the list if found else -1)

        if isinstance(object_UID_or_list, list):
            # the given parameter is a list
            object_lines_list = object_UID_or_list
        else:
            # the given parameter is an object ID
            # get the lines of the object in the ODF lines list
            object_lines_list = self.object_get_data_list(object_UID_or_list)

        for index, line in enumerate(object_lines_list):
            if self.is_line_with_attribute(line):
                # the line contains an attribute
                # recover the attribute name and value present in this line
                (attr_name_str, attr_value_str) = line.split("=", 1)
                if attr_name_str == attribute:
                    return (attr_value_str, index)
                elif is_list_sorted and attr_name_str > attribute:
                    break
        return ('', -1)

    #-------------------------------------------------------------------------------------------------
    def object_get_parent_panel_UID(self, object_UID):
        #--- returns the object ID of the panel (Panel999 or Organ if old panel format) to which belongs the given object ID

        parent_panel_UID = ''

        if object_UID[:5] == 'Panel':
            if len(object_UID) == 8:
                # Panel999 : it has no parent panel
                parent_panel_UID = ''
            else:
                # Panel999NNNNN999
                parent_panel_UID = object_UID[:8]
        else:
            # the object ID is not Panel999 or Panel999Element999, so it is necessarily displayed in the main panel
            if self.new_panel_format:
                parent_panel_UID = 'Panel000'
            else:
                parent_panel_UID = 'Organ'

        return parent_panel_UID

    #-------------------------------------------------------------------------------------------------
    def object_get_parent_manual_UID(self, object_UID):
        #--- returns the object ID of the manual (Manual999) to which belongs the given object ID

        # parse the various Manual999 objects of the dictionnary to see where is referenced the given object ID
        for obj_UID in self.odf_objects_dic:
            if obj_UID[:6] == 'Manual':
                # get the lines of the Manual999 object in the ODF lines list
                object_lines_list = self.object_get_data_list(obj_UID)
                # parse the attributes of this Manual object
                for line in object_lines_list:
                    if self.is_line_with_attribute(line):
                        (attr_name_str, attr_value_str) = line.split("=", 1)
                        if attr_name_str[:-3] == object_UID[:-3] and attr_value_str.zfill(3) == object_UID[-3:]:
                            # object reference found
                            return obj_UID
        return ''

    #-------------------------------------------------------------------------------------------------
    def object_set_data_list(self, object_UID, new_list):
        #--- replace in odf_lines_list the object section lines (object ID + attributes) of the given object ID
        #--- if the object ID doesn't exist yet, or if object_UID is empty, add it in odf_lines_list
        #--- return the object ID if the set has been done properly, else an empty string

        is_new_list_OK = True
        new_object_UID = object_UID

        if self.is_list_empty(new_list):
            # empty list provided
            if object_UID == 'Header':
                # the empty list is in the header of the ODF
                obj_range = self.object_get_lines_range(object_UID)
                if obj_range != (0, 0):
                    # the header has been found in odf_lines_list, replace it by an empty list
                    self.odf_lines_list[obj_range[0]:obj_range[1]] = new_list
                    self.events_log_add("Header is now empty")
            else:
                # for any other object ID, we do nothing, there is a special button to delete an object
                self.events_log_add("None data to apply, click on the button Delete to remove an object")
                is_new_list_OK = False
        else:
            # the new list is not empty
            if object_UID == 'Header':
                # special processing if the object is Header, that is the beginning of the odf_lines_list before the first object ID
                # it can contain only comment or empty lines
                # check that the lines of the new list contain only comments or empty lines
                for line in new_list:
                    if len(line) > 0 and line[0] != ';':
                        self.events_log_add(f"Syntax error in the header : '{line}' is not a comment line")
                        is_new_list_OK = False
                if is_new_list_OK:
                    # replace the header section by the new list
                    obj_range = self.object_get_lines_range(object_UID)
                    self.odf_lines_list[obj_range[0]:obj_range[1]] = new_list
                    self.events_log_add(f"Header updated")

            else:
                # an object section has to be updated or added
                # check the syntax of the new list and the presence of an object ID in its first line
                for index, line in enumerate(new_list):
                    # remove the trailing blank spaces if any
                    line = line.rstrip()
                    if not self.check_odf_line_syntax(line, object_UID):
                        # the line has syntax issue
                        is_new_list_OK = False
                    else:
                        if index == 0:
                            if self.is_line_with_object_UID(line):
                                # the first line contains an object ID, get it
                                new_object_UID = line[1:-1]
                            else:
                                self.events_log_add(f"Syntax error : the first line of the object section must containt an object ID between brackets")
                                is_new_list_OK = False
                        elif self.is_line_with_object_UID(line):
                                self.events_log_add(f"Syntax error : '{line}' an object ID between brackets must be present only in first line of the object section")
                                is_new_list_OK = False

                if is_new_list_OK:
                    # manage the case where the new list contains a new object ID compared to the one given in argument
                    if new_object_UID != object_UID and object_UID != '':
                        self.events_log_add(f"Object {object_UID} unchanged")

                    # recover the range of the object to update in odf_lines_list (if it exists)
                    obj_range = self.object_get_lines_range(new_object_UID)
                    if obj_range != (0, 0):
                        # the object has been found in odf_lines_list, update it with the new list
                        self.odf_lines_list[obj_range[0]:obj_range[1]] = new_list
                        self.events_log_add(f"Object {new_object_UID} updated")
                    else:
                        # the object doesn't exist in odf_lines_list, add it
                        # add a blank line at the beginning of the new list
                        new_list.insert(0, "")
                        # add the new object in odf_lines_list
                        self.odf_lines_list.extend(new_list)
                        self.events_log_add(f"Object {new_object_UID} added")

                    # update the objects dictionnary
                    self.objects_dic_update()

        return new_object_UID if is_new_list_OK else ''

    #-------------------------------------------------------------------------------------------------
    def object_remove(self, object_UID):
        #--- remove from odf_lines_list the object section lines (object ID + attributes) of the given object ID
        #--- ask to the user to confirm the deletion
        #--- return True or False whether the deletion has been done or not

        obj_removed_ok = False

        if messagebox.askokcancel("ODF Editor", "Do you confirm you want to delete the object " + object_UID + " ?"):
            # the user has accepted the deletion
            # recover the range of the object data
            obj_range = self.object_get_lines_range(object_UID)
            if obj_range != (0, 0):
                # the range has been recovered
                # remove the object section in odf_lines_list
                self.odf_lines_list[obj_range[0]:obj_range[1]] = []
                self.events_log_add(f"Object {object_UID} deleted")
                # update the objects dictionnary
                self.objects_dic_update()
                obj_removed_ok = True
            else:
                self.events_log_add(f"Object {object_UID} not deleted because not found")
                obj_removed_ok = False
        else:
            obj_removed_ok = False

        return obj_removed_ok

    #-------------------------------------------------------------------------------------------------
    def is_list_empty(self, list_to_check):
        #--- returns true or false whether the given list contains only empty items or not

        is_empty = True
        for item in list_to_check:
            if item != '':
                is_empty = False
                break

        return is_empty

    #-------------------------------------------------------------------------------------------------
    def is_line_with_object_UID(self, line_to_check):
        #--- returns True or False whether the given line contains an object ID or not (at least 1 character between brackets)

        return (line_to_check[:1] == "[" and line_to_check[-1:] == "]" and len(line_to_check) > 2)

    #-------------------------------------------------------------------------------------------------
    def is_line_with_attribute(self, line_to_check):
        #--- returns True or False whether the given line contains an object attribute or not (at least 3 characters with '=' present not in first position and ';' not in first position)

        return (len(line_to_check) > 3 and line_to_check[0] != ';' and line_to_check[0] != '=' and '=' in line_to_check)

    #-------------------------------------------------------------------------------------------------
    def check_odf_line_syntax(self, line, line_location):
        #--- returns True/False whether the given line string respects the ODF syntax or not
        #--- insert the given line location information in the error log if an error is detected
        #--- the given line string must not have leading/trailing whitespaces (let use str.strip() function on it before the call)

        syntax_is_OK = True

        if line[:1] == "[":  # line normally with an object ID
            if line[-1:] != "]":  # object ID without closing bracket
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the character ']' is missing at the end to define an object ID")
                syntax_is_OK = False
            elif len(line) < 3:   # object ID with no string between the brackets
                self.events_log_add(f"Syntax error in {line_location} '{line}' : an object ID must be defined between the brackets")
                syntax_is_OK = False
            elif not line[1:-1].isalnum():  # object ID not containing only alphanumeric characters
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the object ID must contain only alphanumeric characters")
                syntax_is_OK = False

        elif len(line) > 0 and line[:1] != ";":  # it is not an empty or comment line
            if '=' not in line:    # none equal character in the line
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the character '=' is missing to define an attribute=value pair or it may be a comment line")
                syntax_is_OK = False
            elif line[:1] == '=':  # the line starts by an equal character
                self.events_log_add(f"Syntax error in {line_location} '{line}' : the character '=' must not start a line")
                syntax_is_OK = False
            else:
                attr_name_str = line.rpartition("=")[0]  # recover the attribute at the left of =
                for char in attr_name_str:
                    if char not in ALLOWED_CHARS_4_FIELDS:
                        self.events_log_add(f"Syntax error in {line_location} '{line}' : the attribute '{attr_name_str}' must contain only alphanumeric or '_' characters")
                        syntax_is_OK = False
                        break

        return syntax_is_OK

    #-------------------------------------------------------------------------------------------------
    def check_odf_lines(self, progress_status_update_fct):
        #--- check the consistency of the data which are present in odf_lines_list

        if self.check_files_names == '':
            # ask the user if he wants to check the files names
            self.check_files_names = messagebox.askyesno("ODF Editor", "Do you want to check the files names ? \nThis choice will be kept until the next ODF opening")

        self.check_nb_attr = 0

        # update the panel format flag
        self.check_odf_panel_format()
        if self.new_panel_format:
            self.events_log_add("New panel format")
        else:
            self.events_log_add("Old panel format")

        # check the syntax of the header of the ODF
        object_lines_list = self.object_get_data_list('Header')
        for line in object_lines_list:
            self.check_odf_line_syntax(line, "the header")

        # check the presence of the Organ object (which is the root of all the other objects)
        if 'Organ' not in self.odf_objects_dic:
            self.events_log_add("Error : the object Organ is not defined")

        for object_UID in self.odf_objects_dic:
            # parse the objects of the objects dictionnary keys

            # recover the lines of the object section in odf_lines_list
            object_lines_list = self.object_get_data_list(object_UID)

            # update in the GUI the name of the checked object ID
            progress_status_update_fct(f'Checking {object_UID}...')

            if len(object_lines_list) > 0:
                # lines have been recovered for the current object ID

                # check the syntax of the lines of the object
                for line in object_lines_list:
                    self.check_odf_line_syntax(line, object_UID)

                # remove the first line of the object section which contains the object ID
                object_lines_list.pop(0)

                # sort the lines list to make faster the search which is done in check_attribute_value
                object_lines_list.sort()

                # remove the first line while it is empty (after the sorting the empty lines are all in first positions)
                while len(object_lines_list) > 0 and object_lines_list[0] == '':
                    object_lines_list.pop(0)

                # check if the attributes are all uniques in the object section
                self.check_attributes_unicity(object_UID, object_lines_list)

                # generate the generic object ID (Manual999 instead of Manual001 for example)
                gen_object_UID = ''
                for c in object_UID:
                    gen_object_UID += '9' if c.isdigit() else c

                # check the attributes and values of the object
                if gen_object_UID == 'Organ':
                    self.check_object_Organ(object_UID, object_lines_list)
                elif gen_object_UID == 'Coupler999':
                    self.check_object_Coupler(object_UID, object_lines_list)
                elif gen_object_UID == 'Divisional999':
                    self.check_object_Divisional(object_UID, object_lines_list)
                elif gen_object_UID == 'DivisionalCoupler999':
                    self.check_object_DivisionalCoupler(object_UID, object_lines_list)
                elif gen_object_UID == 'Enclosure999':
                    self.check_object_Enclosure(object_UID, object_lines_list)
                elif gen_object_UID == 'General999':
                    self.check_object_General(object_UID, object_lines_list)
                elif gen_object_UID == 'Image999':
                    self.check_object_Image(object_UID, object_lines_list)
                elif gen_object_UID == 'Label999':
                    self.check_object_Label(object_UID, object_lines_list)
                elif gen_object_UID == 'Manual999':
                    self.check_object_Manual(object_UID, object_lines_list)
                elif gen_object_UID == 'Panel999':
                    self.check_object_Panel(object_UID, object_lines_list)
                elif gen_object_UID == 'Panel999Element999':
                    self.check_object_PanelElement(object_UID, object_lines_list)
                elif gen_object_UID[:5] == 'Panel': # Panel999Coupler999, Panel999Divisional999, Panel999Image999, ...
                    self.check_object_PanelOther(object_UID, object_lines_list)
                elif gen_object_UID == 'Rank999':
                    self.check_object_Rank(object_UID, object_lines_list)
                elif gen_object_UID == 'ReversiblePiston999':
                    self.check_object_ReversiblePiston(object_UID, object_lines_list)
                elif gen_object_UID == 'SetterElement999':
                    self.check_object_SetterElement(object_UID, object_lines_list)
                elif gen_object_UID == 'Stop999':
                    self.check_object_Stop(object_UID, object_lines_list)
                elif gen_object_UID == 'Switch999':
                    self.check_object_Switch(object_UID, object_lines_list)
                elif gen_object_UID == 'Tremulant999':
                    self.check_object_Tremulant(object_UID, object_lines_list)
                elif gen_object_UID == 'WindchestGroup999':
                    self.check_object_WindchestGroup(object_UID, object_lines_list)
                else:
                    # the object ID has not been recognized
                    self.events_log_add(f"Error : the object identifier {object_UID} is invalid or misspelled")
                    # empty the lines list of the object which is not recognized, to not display in the log its attributes which have not been checked
                    object_lines_list = []

                # report in the logs if attributes have not been recognized in the object section, so they are not expected or are misspelled
                # each attribute checked by the function check_attribute_value() has been removed in the lines list after its check
                # so the one still in the list have not been recognized by the check_object_xxx functions called before
                for line in object_lines_list:
                    if self.is_line_with_attribute(line):
                        self.check_nb_attr += 1
                        (attr_name_str, attr_value_str) = line.split("=", 1)
                        self.events_log_add(f"Warning in {object_UID} : the attribute {attr_name_str} is not expected in this object or is misspelled")

        # report in the logs if Couplers / Divisionals / Stops are referenced in none object (Manual or WindchestGroup), so they are not used
        for obj_UID, obj_prop_list in self.odf_objects_dic.items():
            if obj_UID != 'Organ' and len(obj_prop_list[IDX_OBJ_PAR]) == 0:
                # the object has none parent in the objects dictionnary
                self.events_log_add(f"Warning : the object {obj_UID} is not used")

        # display in the log the number of checked attributes
        self.events_log_add(f"{self.check_nb_attr} attributes checked")

        # display in the log if none error has been detected
        if len(self.events_log_list) <= 3:  # 3 lines minimum : check start message + detected panel format + number of checked attributes
            self.events_log_add("None error found")

    #-------------------------------------------------------------------------------------------------
    def check_odf_panel_format(self):
        #--- check which is the panel format used in the ODF (new or old) and update the flag

        (attr_value_str, attr_idx) = self.object_get_attribute_value('Panel000', 'NumberOfGUIElements')
        self.new_panel_format = (attr_value_str.isdigit() and int(attr_value_str) >= 0)

    #-------------------------------------------------------------------------------------------------
    def check_object_Organ(self, object_UID, lines_list):
        #--- check the data of an Organ object section which the lines are in the given lines list

        # required attributes
        self.check_attribute_value(object_UID, lines_list, 'ChurchName', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_UID, lines_list, 'ChurchAddress', ATTR_TYPE_STRING, True)

        ret = self.check_attribute_value(object_UID, lines_list, 'HasPedals', ATTR_TYPE_BOOLEAN, True)
        if ret == "Y" and not ('Manual000' in self.odf_objects_dic):
            self.events_log_add(f"Error in {object_UID} : HasPedals=Y but no Manual000 object is defined")
        elif ret == "N" and ('Manual000' in self.odf_objects_dic):
            self.events_log_add(f"Error in {object_UID} : HasPedals=N whereas a Manual000 object is defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfDivisionalCouplers', ATTR_TYPE_INTEGER, True, 0, 8)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('DivisionalCoupler')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfDivisionalCouplers={ret} whereas {count} DivisionalCoupler object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfEnclosures', ATTR_TYPE_INTEGER, True, 0, 50)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Enclosure')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfEnclosures={ret} whereas {count} Enclosure object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfGenerals', ATTR_TYPE_INTEGER, True, 0, 99)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('General')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfGenerals={ret} whereas {count} General object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfManuals', ATTR_TYPE_INTEGER, True, 1, 16)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Manual')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfManuals={ret} whereas {count} Manual object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfPanels', ATTR_TYPE_INTEGER, self.new_panel_format, 0, 100)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Panel')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfPanels={ret} whereas {count} Panel object(s) defined")

        if self.new_panel_format and not ('Panel000' in self.odf_objects_dic):
            self.events_log_add(f"Error : new panel format used but no Panel000 object is defined")
        elif not self.new_panel_format and ('Panel000' in self.odf_objects_dic):
            self.events_log_add(f"Error in {object_UID} : old panel format used whereas a Panel000 is defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfReversiblePistons', ATTR_TYPE_INTEGER, True, 0, 32)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('ReversiblePiston')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfReversiblePistons={ret} whereas {count} ReversiblePiston object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, 10)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Tremulant')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfTremulants={ret} whereas {count} Tremulant object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfWindchestGroups', ATTR_TYPE_INTEGER, True, 1, 50)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('WindchestGroup')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfWindchestGroups={ret} whereas {count} WindchestGroup object(s) defined")

        self.check_attribute_value(object_UID, lines_list, 'DivisionalsStoreIntermanualCouplers', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DivisionalsStoreIntramanualCouplers', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DivisionalsStoreTremulants', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'GeneralsStoreDivisionalCouplers', ATTR_TYPE_BOOLEAN, True)

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'OrganBuilder', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'OrganBuildDate', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'OrganComments', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'RecordingDetails', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'InfoFilename', ATTR_TYPE_STRING, False)

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfImages', ATTR_TYPE_INTEGER, False, 0, 999) # old panel format
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Image')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfImages={ret} whereas {count} Image object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfLabels', ATTR_TYPE_INTEGER, False, 0, 999)  # old panel format
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Label')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfLabels={ret} whereas {count} Label object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfRanks', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Rank')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfRanks={ret} whereas {count} Rank object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSetterElements', ATTR_TYPE_INTEGER, False, 0, 999)  # old panel format
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('SetterElement')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfSetterElements={ret} whereas {count} SetterElement object(s) defined")

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) >= 0:
            count = self.objects_type_count('Switch')
            if count != int(ret):
                self.events_log_add(f"Error in {object_UID} : NumberOfSwitches={ret} whereas {count} Switch object(s) defined")

        self.check_attribute_value(object_UID, lines_list, 'CombinationsStoreNonDisplayedDrawstops', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'AmplitudeLevel', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_UID, lines_list, 'Gain', ATTR_TYPE_FLOAT, False, -120, 40)
        self.check_attribute_value(object_UID, lines_list, 'PitchTuning', ATTR_TYPE_FLOAT, False, -1200, 1200)
        self.check_attribute_value(object_UID, lines_list, 'TrackerDelay', ATTR_TYPE_FLOAT, False, 0, 10000)

        if not self.new_panel_format:
            # if old parnel format, the Organ object contains panel attributes
            self.check_object_Panel(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Button(self, object_UID, lines_list):
        #--- check the data of a Button object section which the lines are in the given lines list

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'ShortcutKey', ATTR_TYPE_INTEGER, False, 0, 255)
        self.check_attribute_value(object_UID, lines_list, 'StopControlMIDIKeyNumber', ATTR_TYPE_INTEGER, False, 0, 127)
        self.check_attribute_value(object_UID, lines_list, 'MIDIProgramChangeNumber', ATTR_TYPE_INTEGER, False, 1, 128)
        self.check_attribute_value(object_UID, lines_list, 'Displayed', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'DisplayInInvertedState', ATTR_TYPE_BOOLEAN, False)

        display_as_piston = self.check_attribute_value(object_UID, lines_list, 'DisplayAsPiston', ATTR_TYPE_BOOLEAN, False)
        if display_as_piston == '':
            # attribute not defined, set its default value
            if (any(str in object_UID for str in ('Divisional', 'General')) or
                ('Element' in object_UID and any(str in self.object_get_attribute_value(object_UID, 'Type') for str in ('Divisional', 'General')))):
                # the object is a Divisional or General button or GUI element, so it must be displayed as a piston by default
                display_as_piston = 'Y'
            else:
                display_as_piston = 'N'

        self.check_attribute_value(object_UID, lines_list, 'DispLabelColour', ATTR_TYPE_COLOR, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelFontSize', ATTR_TYPE_FONT_SIZE, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelFontName', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelText', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'DispKeyLabelOnLeft', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'DispImageNum', ATTR_TYPE_INTEGER, False, 1, 5 if display_as_piston == 'Y' else 6)
        self.check_attribute_value(object_UID, lines_list, 'DispButtonRow', ATTR_TYPE_INTEGER, False, 0, 199)
        self.check_attribute_value(object_UID, lines_list, 'DispButtonCol', ATTR_TYPE_INTEGER, False, 1, 32)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopRow', ATTR_TYPE_INTEGER, False, 1, 199)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopCol', ATTR_TYPE_INTEGER, False, 1, 12)
        image_on = self.check_attribute_value(object_UID, lines_list, 'ImageOn', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_UID, lines_list, 'ImageOff', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_UID, lines_list, 'MaskOn', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_UID, lines_list, 'MaskOff', ATTR_TYPE_FILE_NAME, False)

        # get the dimensions of the parent panel
        panel_UID = self.object_get_parent_panel_UID(object_UID)
        (value, idx) = self.object_get_attribute_value(panel_UID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(panel_UID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_UID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        width = self.check_attribute_value(object_UID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        height = self.check_attribute_value(object_UID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)
        max_width = int(width) if width.isdigit() else panel_width
        max_height = int(height) if height.isdigit() else panel_height

        # get the dimensions of the button bitmap
        if image_on != '':
            # an image is defined to display the button
            if self.check_files_names:
                # get the sizes of the image in the file which is existing
                modif_path = image_on.replace('\\', '/')
                im = Image.open(os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = im.size[1]
                bitmap_height = im.size[0]
##                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
##                bitmap_width = photo.width()
##                bitmap_height = photo.height()
            else:
                bitmap_width = 500  # arbritrary default value
                bitmap_height = 200 # arbritrary default value
        else:
            # no image file defined, get the dimensions of the internal bitmap (piston or drawstop)
            if display_as_piston == 'Y':
                bitmap_width = bitmap_height = 32
            else:
                bitmap_width = bitmap_height = 62

        self.check_attribute_value(object_UID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_UID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        self.check_attribute_value(object_UID, lines_list, 'MouseRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'MouseRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        mouse_rect_width = self.check_attribute_value(object_UID, lines_list, 'MouseRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        mouse_rect_height = self.check_attribute_value(object_UID, lines_list, 'MouseRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if mouse_rect_width.isdigit() and mouse_rect_height.isdigit():
            mouse_radius = max(int(mouse_rect_width), int(mouse_rect_height))
        else:
            mouse_radius = max(bitmap_width, bitmap_height)
        self.check_attribute_value(object_UID, lines_list, 'MouseRadius', ATTR_TYPE_INTEGER, False, 0, mouse_radius)

        self.check_attribute_value(object_UID, lines_list, 'TextRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'TextRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        text_rect_width = self.check_attribute_value(object_UID, lines_list, 'TextRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'TextRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if text_rect_width.isdigit():
            text_break_width = int(text_rect_width)
        else:
            text_break_width = bitmap_width
        self.check_attribute_value(object_UID, lines_list, 'TextBreakWidth', ATTR_TYPE_INTEGER, False, 0, text_break_width)

    #-------------------------------------------------------------------------------------------------
    def check_object_Coupler(self, object_UID, lines_list):
        #--- check the data of a Coupler object section which the lines are in the given lines list

        # required attributes
        ret1 = self.check_attribute_value(object_UID, lines_list, 'UnisonOff', ATTR_TYPE_BOOLEAN, True)
        ret2 = self.check_attribute_value(object_UID, lines_list, 'CouplerType', ATTR_TYPE_COUPLER_TYPE, False)  # optional but here to recover its value used after
        self.check_attribute_value(object_UID, lines_list, 'DestinationManual', ATTR_TYPE_INTEGER, True if ret1 == 'N' else False, 0, 16) # conditional required/optional
        self.check_attribute_value(object_UID, lines_list, 'DestinationKeyshift', ATTR_TYPE_INTEGER, True if ret1 == 'N' else False, -24, 24) # conditional required/optional

        is_required = (ret1 == 'N' and not(ret2.upper() in ('MELODY', 'BASS')))
        self.check_attribute_value(object_UID, lines_list, 'CoupleToSubsequentUnisonIntermanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_UID, lines_list, 'CoupleToSubsequentUpwardIntermanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_UID, lines_list, 'CoupleToSubsequentDownwardIntermanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_UID, lines_list, 'CoupleToSubsequentUpwardIntramanualCouplers', ATTR_TYPE_BOOLEAN, is_required)
        self.check_attribute_value(object_UID, lines_list, 'CoupleToSubsequentDownwardIntramanualCouplers', ATTR_TYPE_BOOLEAN, is_required)

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'FirstMIDINoteNumber', ATTR_TYPE_INTEGER, False, 0, 127)
        self.check_attribute_value(object_UID, lines_list, 'NumberOfKeys', ATTR_TYPE_INTEGER, False, 0, 127)

        # a Coupler has in addition the attributes of a DrawStop
        self.check_object_DrawStop(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Divisional(self, object_UID, lines_list):
        #--- check the data of a Divisional object section which the lines are in the given lines list

        # recover the ID of manual in which is referenced this Divisional
        parent_manual_UID = self.object_get_parent_manual_UID(object_UID)

        # required attributes
        (ret, idx) = self.object_get_attribute_value(parent_manual_UID, 'NumberOfCouplers')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Coupler{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        (ret, idx) = self.object_get_attribute_value(parent_manual_UID, 'NumberOfStops')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Stop{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        (ret, idx) = self.object_get_attribute_value(parent_manual_UID, 'NumberOfTremulants')
        max = int(ret) if ret.isdigit() else 10
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Tremulant{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Protected', ATTR_TYPE_BOOLEAN, False)

        (ret, idx) = self.object_get_attribute_value(parent_manual_UID, 'NumberOfSwitches')
        max = int(ret) if ret.isdigit() else 999
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Switch{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # a Divisional has in addition the attributes of a Push Button
        self.check_object_PushButton(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_DivisionalCoupler(self, object_UID, lines_list):
        #--- check the data of a Divisional Coupler object section which the lines are in the given lines list

        # required attributes
        self.check_attribute_value(object_UID, lines_list, 'BiDirectionalCoupling', ATTR_TYPE_BOOLEAN, True)

        (ret, idx) = self.object_get_attribute_value('Organ', 'NumberOfManuals')
        max = int(ret) if ret.isdigit() else 16
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfManuals', ATTR_TYPE_INTEGER, True, 1, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f"Manual{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)

        # a Divisional Coupler has in addition the attributes of a DrawStop
        self.check_object_DrawStop(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_DrawStop(self, object_UID, lines_list):
        #--- check the data of a DrawStop object section which the lines are in the given lines list

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Function', ATTR_TYPE_DRAWSTOP_FCT, False)

        (ret, idx) = self.object_get_attribute_value('Organ', 'NumberOfSwitches')
        max = int(ret) if ret.isdigit() else 999
        switch_id = int(object_UID[-3:]) if (object_UID[-3:].isdigit() and object_UID[:-3] == 'Switch') else 999
        ret = self.check_attribute_value(object_UID, lines_list, 'SwitchCount', ATTR_TYPE_INTEGER, False, 1, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f"Switch{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                if switch_id != 999:
                    self.check_attribute_value(object_UID, lines_list, f"Switch{str(idx).zfill(3)}", ATTR_TYPE_INTEGER, True, 1, switch_id - 1)

        self.check_attribute_value(object_UID, lines_list, 'DefaultToEngaged', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'GCState', ATTR_TYPE_INTEGER, False, -1, 1)
        self.check_attribute_value(object_UID, lines_list, 'StoreInDivisional', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'StoreInGeneral', ATTR_TYPE_BOOLEAN, False)

        # a Drawstop has in addition the attributes of a Button
        self.check_object_Button(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Enclosure(self, object_UID, lines_list):
        #--- check the data of an Enclosure object section which the lines are in the given lines list

        # required attributes
        # none required attribute

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'AmpMinimumLevel', ATTR_TYPE_INTEGER, False, 0, 100)
        self.check_attribute_value(object_UID, lines_list, 'MIDIInputNumber', ATTR_TYPE_INTEGER, False, 0, 100)
        self.check_attribute_value(object_UID, lines_list, 'Displayed', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelColour', ATTR_TYPE_COLOR, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelFontSize', ATTR_TYPE_FONT_SIZE, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelFontName', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelText', ATTR_TYPE_STRING, False)
        self.check_attribute_value(object_UID, lines_list, 'EnclosureStyle', ATTR_TYPE_INTEGER, False, 1, 4)

        ret = self.check_attribute_value(object_UID, lines_list, 'BitmapCount', ATTR_TYPE_INTEGER, False, 1, 127)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                image = self.check_attribute_value(object_UID, lines_list, f'Bitmap{str(idx).zfill(3)}', ATTR_TYPE_FILE_NAME, True)
                self.check_attribute_value(object_UID, lines_list, f'Mask{str(idx).zfill(3)}', ATTR_TYPE_FILE_NAME, False)
            # get the dimensions of the last enclosure bitmap
            if image != '' and self.check_files_names:
                # an image is defined to display the enclosure
                # get the sizes of the image in the file which is existing
                modif_path = image.replace('\\', '/')
                im = Image.open(os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = im.size[1]
                bitmap_height = im.size[0]
##                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
##                bitmap_width = photo.width()
##                bitmap_height = photo.height()
            else:
                bitmap_width = 100  # arbritrary default value
                bitmap_height = 200 # arbritrary default value
        else:
            # no image file defined, get the dimensions of the internal bitmap
            bitmap_width = 46
            bitmap_height = 61

        # get the dimensions of the parent panel
        panel_UID = self.object_get_parent_panel_UID(object_UID)
        (value, idx) = self.object_get_attribute_value(panel_UID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(panel_UID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_UID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        width = self.check_attribute_value(object_UID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        height = self.check_attribute_value(object_UID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)
        max_width = int(width) if width.isdigit() else panel_width
        max_height = int(height) if height.isdigit() else panel_height

        self.check_attribute_value(object_UID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_UID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        self.check_attribute_value(object_UID, lines_list, 'MouseRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'MouseRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        self.check_attribute_value(object_UID, lines_list, 'MouseRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        mouse_rect_height = self.check_attribute_value(object_UID, lines_list, 'MouseRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if mouse_rect_height.isdigit():
            max_start = int(mouse_rect_height)
        else:
            max_start = 200
        mouse_axis_start = self.check_attribute_value(object_UID, lines_list, 'MouseAxisStart', ATTR_TYPE_INTEGER, False, 0, max_start)

        if mouse_axis_start.isdigit():
            min_end = int(mouse_axis_start)
        else:
            min_end = 200
        self.check_attribute_value(object_UID, lines_list, 'MouseAxisEnd', ATTR_TYPE_INTEGER, False, min_end, max_start)

        self.check_attribute_value(object_UID, lines_list, 'TextRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'TextRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        text_rect_width = self.check_attribute_value(object_UID, lines_list, 'TextRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'TextRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if text_rect_width.isdigit():
            text_break_width = int(text_rect_width)
        else:
            text_break_width = bitmap_width
        self.check_attribute_value(object_UID, lines_list, 'TextBreakWidth', ATTR_TYPE_INTEGER, False, 0, text_break_width)

    #-------------------------------------------------------------------------------------------------
    def check_object_General(self, object_UID, lines_list):
        #--- check the data of a General object section which the lines are in the given lines list

        is_general_obj = object_UID.startswith('General') # some mandatory attributes are not mandatory for objects which inherit the General attributes

        # required attributes
        max = self.objects_type_count('Coupler')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, is_general_obj, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'CouplerNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)
                self.check_attribute_value(object_UID, lines_list, f'CouplerManual{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('DivisionalCoupler')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfDivisionalCouplers', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'DivisionalCouplerNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Stop')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, is_general_obj, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'StopNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)
                self.check_attribute_value(object_UID, lines_list, f'StopManual{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Tremulant')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, is_general_obj, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'TremulantNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        max = self.objects_type_count('Switch')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'SwitchNumber{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        self.check_attribute_value(object_UID, lines_list, 'Protected', ATTR_TYPE_BOOLEAN, False)

        # a General has in addition the attributes of a Push Button
        self.check_object_PushButton(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Image(self, object_UID, lines_list):
        #--- check the data of an Image object section which the lines are in the given lines list

        # required attributes
        image = self.check_attribute_value(object_UID, lines_list, 'Image', ATTR_TYPE_FILE_NAME, True)

        # get the dimensions of the parent panel
        parent_panel_UID = self.object_get_parent_panel_UID(object_UID)
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Mask', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_UID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        self.check_attribute_value(object_UID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)

        # get the dimensions of the image bitmap
        if image != '':
            # an image is defined
            if self.check_files_names:
                # get the sizes of the image in the file which is existing
                modif_path = image.replace('\\', '/')
                im = Image.open(os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = im.size[1]
                bitmap_height = im.size[0]
##                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
##                bitmap_width = photo.width()
##                bitmap_height = photo.height()
            else:
                bitmap_width = panel_width
                bitmap_height = panel_height
        else:
            # no image file defined
            bitmap_width = panel_width
            bitmap_height = panel_height

        self.check_attribute_value(object_UID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_UID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

    #-------------------------------------------------------------------------------------------------
    def check_object_Label(self, object_UID, lines_list):
        #--- check the data of a Label object section which the lines are in the given lines list

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, False)
        ret1 = self.check_attribute_value(object_UID, lines_list, 'FreeXPlacement', ATTR_TYPE_BOOLEAN, False)
        ret2 = self.check_attribute_value(object_UID, lines_list, 'FreeYPlacement', ATTR_TYPE_BOOLEAN, False)

        # get the dimensions of the parent panel
        parent_panel_UID = self.object_get_parent_panel_UID(object_UID)
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_UID, lines_list, 'DispXpos', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'DispYpos', ATTR_TYPE_INTEGER, False, 0, panel_height)

        self.check_attribute_value(object_UID, lines_list, 'DispAtTopOfDrawstopCol', ATTR_TYPE_BOOLEAN, ret2 == 'N')

        # get the number of drawstop columns in the parent panel
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispDrawstopCols')
        columns_nb = int(value) if value.isdigit() else 12
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopCol', ATTR_TYPE_INTEGER, ret1 == 'N', 1, columns_nb)

        self.check_attribute_value(object_UID, lines_list, 'DispSpanDrawstopColToRight', ATTR_TYPE_BOOLEAN, True if ret1 == 'N' else False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelColour', ATTR_TYPE_COLOR, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelFontSize', ATTR_TYPE_FONT_SIZE, False)
        self.check_attribute_value(object_UID, lines_list, 'DispLabelFontName', ATTR_TYPE_STRING, False)
        image_num = self.check_attribute_value(object_UID, lines_list, 'DispImageNum', ATTR_TYPE_INTEGER, False, 1, 12)
        image = self.check_attribute_value(object_UID, lines_list, 'Image', ATTR_TYPE_FILE_NAME, False)
        self.check_attribute_value(object_UID, lines_list, 'Mask', ATTR_TYPE_FILE_NAME, False)

        self.check_attribute_value(object_UID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)
        width = self.check_attribute_value(object_UID, lines_list, 'Width', ATTR_TYPE_INTEGER, False, 0, panel_width)
        height = self.check_attribute_value(object_UID, lines_list, 'Height', ATTR_TYPE_INTEGER, False, 0, panel_height)
        max_width = int(width) if width.isdigit() else panel_width
        max_height = int(height) if height.isdigit() else panel_height

        # get the dimensions of the label bitmap
        if image != '':
            # an image is defined to display the label
            if self.check_files_names:
                # get the sizes of the image in the file which is existing
                modif_path = image.replace('\\', '/')
                im = Image.open(os.path.dirname(self.odf_file_name) + '/' + modif_path)
                bitmap_width = im.size[1]
                bitmap_height = im.size[0]
##                photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
##                bitmap_width = photo.width()
##                bitmap_height = photo.height()
            else:
                bitmap_width = 400  # arbritrary default value
                bitmap_height = 100 # arbritrary default value
        else:
            if   image_num == '1':  bitmap_width = 80; bitmap_height = 25
            elif image_num == '2':  bitmap_width = 80; bitmap_height = 50
            elif image_num == '3':  bitmap_width = 80; bitmap_height = 25
            elif image_num == '4':  bitmap_width = 160; bitmap_height = 25
            elif image_num == '5':  bitmap_width = 200; bitmap_height = 50
            elif image_num == '6':  bitmap_width = 80; bitmap_height = 50
            elif image_num == '7':  bitmap_width = 80; bitmap_height = 25
            elif image_num == '8':  bitmap_width = 160; bitmap_height = 25
            elif image_num == '9':  bitmap_width = 80; bitmap_height = 50
            elif image_num == '10': bitmap_width = 80; bitmap_height = 25
            elif image_num == '11': bitmap_width = 160; bitmap_height = 25
            else:                   bitmap_width = 200; bitmap_height = 50


        self.check_attribute_value(object_UID, lines_list, 'TileOffsetX', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
        self.check_attribute_value(object_UID, lines_list, 'TileOffsetY', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        self.check_attribute_value(object_UID, lines_list, 'TextRectLeft', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'TextRectTop', ATTR_TYPE_INTEGER, False, 0, max_height)
        text_rect_width = self.check_attribute_value(object_UID, lines_list, 'TextRectWidth', ATTR_TYPE_INTEGER, False, 0, max_width)
        self.check_attribute_value(object_UID, lines_list, 'TextRectHeight', ATTR_TYPE_INTEGER, False, 0, max_height)

        if text_rect_width.isdigit():
            text_break_width = int(text_rect_width)
        else:
            text_break_width = bitmap_width
        self.check_attribute_value(object_UID, lines_list, 'TextBreakWidth', ATTR_TYPE_INTEGER, False, 0, text_break_width)

    #-------------------------------------------------------------------------------------------------
    def check_object_Manual(self, object_UID, lines_list):
        #--- check the data of a Manual object section which the lines are in the given lines list

        is_manual_obj = object_UID.startswith('Manual') # some mandatory attributes are not mandatory for objects which inherit the Manual attributes

        # required attributes
        self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, is_manual_obj)
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfLogicalKeys', ATTR_TYPE_INTEGER, is_manual_obj, 1, 192)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                # attributes Key999xxx
                image = self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}ImageOn', ATTR_TYPE_FILE_NAME, False)
                if image != "":
                    # check the other attributes for this key only if an image on is defined
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}ImageOff', ATTR_TYPE_FILE_NAME, False)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}MaskOn', ATTR_TYPE_FILE_NAME, False)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}MaskOff', ATTR_TYPE_FILE_NAME, False)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}Width', ATTR_TYPE_INTEGER, False, 0, 500)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}Offset', ATTR_TYPE_INTEGER, False, -500, 500)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}YOffset', ATTR_TYPE_INTEGER, False, 0, 500)

                    # get the dimensions of the key bitmap
                    # an image is defined to display the key
                    if self.check_files_names:
                        # get the sizes of the image in the file which is existing
                        modif_path = image.replace('\\', '/')
                        im = Image.open(os.path.dirname(self.odf_file_name) + '/' + modif_path)
                        bitmap_width = im.size[1]
                        bitmap_height = im.size[0]
##                        photo = PhotoImage(file = os.path.dirname(self.odf_file_name) + '/' + modif_path)
##                        bitmap_width = photo.width()
##                        bitmap_height = photo.height()
                    else:
                        bitmap_width = 100  # arbritrary default value
                        bitmap_height = 300 # arbritrary default value

                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}MouseRectLeft', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}MouseRectTop', ATTR_TYPE_INTEGER, False, 0, bitmap_height)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}MouseRectWidth', ATTR_TYPE_INTEGER, False, 0, bitmap_width)
                    self.check_attribute_value(object_UID, lines_list, f'Key{str(idx).zfill(3)}MouseRectHeight', ATTR_TYPE_INTEGER, False, 0, bitmap_height)

        logical_keys_nb = int(ret) if ret.isdigit() else 192
        self.check_attribute_value(object_UID, lines_list, 'FirstAccessibleKeyLogicalKeyNumber', ATTR_TYPE_INTEGER, is_manual_obj, 1, logical_keys_nb)
        self.check_attribute_value(object_UID, lines_list, 'FirstAccessibleKeyMIDINoteNumber', ATTR_TYPE_INTEGER, is_manual_obj, 0, 127)

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfAccessibleKeys', ATTR_TYPE_INTEGER, is_manual_obj, 0, 85)
        accessible_keys_nb = int(ret) if ret.isdigit() else 85

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Coupler{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfDivisionals', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Divisional{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Stop{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Switch')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Switch{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Tremulant')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, False, 0, max)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Tremulant{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        for idx in range(0, 128):
            self.check_attribute_value(object_UID, lines_list, f'MIDIKey{str(idx).zfill(3)}', ATTR_TYPE_INTEGER, False, 0, 127)

        self.check_attribute_value(object_UID, lines_list, 'MIDIInputNumber', ATTR_TYPE_INTEGER, False, 0, 200)
        self.check_attribute_value(object_UID, lines_list, 'Displayed', ATTR_TYPE_BOOLEAN, False)

        # get the dimensions of the parent panel
        parent_panel_UID = self.object_get_parent_panel_UID(object_UID)
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispScreenSizeHoriz')
        panel_width = int(value) if value.isdigit() else 3000
        (value, idx) = self.object_get_attribute_value(parent_panel_UID, 'DispScreenSizeVert')
        panel_height = int(value) if value.isdigit() else 2000

        self.check_attribute_value(object_UID, lines_list, 'PositionX', ATTR_TYPE_INTEGER, False, 0, panel_width)
        self.check_attribute_value(object_UID, lines_list, 'PositionY', ATTR_TYPE_INTEGER, False, 0, panel_height)

        self.check_attribute_value(object_UID, lines_list, 'DispKeyColourInverted', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'DispKeyColourWooden', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'DisplayFirstNote', ATTR_TYPE_INTEGER, False, 0, 127)

        ret = self.check_attribute_value(object_UID, lines_list, 'DisplayKeys', ATTR_TYPE_INTEGER, False, 1, accessible_keys_nb)
        if ret.isdigit() and int(ret) > 0:
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'DisplayKey{str(idx).zfill(3)}', ATTR_TYPE_INTEGER, False, 0, 127)
                self.check_attribute_value(object_UID, lines_list, f'DisplayKey{str(idx).zfill(3)}Note', ATTR_TYPE_INTEGER, False, 0, 127)

        # optional attributes with the KEYTYPE format
        ImageOn_First_keytype = '' # variable to store if the first attribute have been already checked for the ImageOn key type
        ImageOff_First_keytype = ''
        MaskOn_First_keytype = ''
        MaskOff_First_keytype = ''
        Width_First_keytype = ''
        Offset_First_keytype = ''
        YOffset_First_keytype = ''

        ImageOn_Last_keytype = ''
        ImageOff_Last_keytype = ''
        MaskOn_Last_keytype = ''
        MaskOff_Last_keytype = ''
        Width_Last_keytype = ''
        Offset_Last_keytype = ''
        YOffset_Last_keytype = ''

        for keytype in ('C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'B'):
            self.check_attribute_value(object_UID, lines_list, f'ImageOn_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_UID, lines_list, f'ImageOff_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_UID, lines_list, f'MaskOn_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_UID, lines_list, f'MaskOff_{keytype}', ATTR_TYPE_FILE_NAME, False)
            self.check_attribute_value(object_UID, lines_list, f'Width_{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            self.check_attribute_value(object_UID, lines_list, f'Offset_{keytype}', ATTR_TYPE_INTEGER, False, -500, 500)
            self.check_attribute_value(object_UID, lines_list, f'YOffset_{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            # the First and Last attributes are checked only once for each key property
            # so if there is more than one First or Last definition it will appear in the warning logs because it will not have been checked here
            if ImageOn_First_keytype == '' : ImageOn_First_keytype = self.check_attribute_value(object_UID, lines_list, f'ImageOn_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if ImageOff_First_keytype == '' : ImageOff_First_keytype = self.check_attribute_value(object_UID, lines_list, f'ImageOff_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOn_First_keytype == '' : MaskOn_First_keytype = self.check_attribute_value(object_UID, lines_list, f'MaskOn_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOff_First_keytype == '' : MaskOff_First_keytype = self.check_attribute_value(object_UID, lines_list, f'MaskOff_First{keytype}', ATTR_TYPE_FILE_NAME, False)
            if Width_First_keytype == '' : Width_First_keytype = self.check_attribute_value(object_UID, lines_list, f'Width_First{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            if Offset_First_keytype == '' : Offset_First_keytype = self.check_attribute_value(object_UID, lines_list, f'Offset_First{keytype}', ATTR_TYPE_INTEGER, False, -500, 500)
            if YOffset_First_keytype == '' : YOffset_First_keytype = self.check_attribute_value(object_UID, lines_list, f'YOffset_First{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)

            if ImageOn_Last_keytype == '' : ImageOn_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'ImageOn_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if ImageOff_Last_keytype == '' : ImageOff_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'ImageOff_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOn_Last_keytype == '' : MaskOn_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'MaskOn_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if MaskOff_Last_keytype == '' : MaskOff_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'MaskOff_Last{keytype}', ATTR_TYPE_FILE_NAME, False)
            if Width_Last_keytype == '' : Width_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'Width_Last{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)
            if Offset_Last_keytype == '' : Offset_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'Offset_Last{keytype}', ATTR_TYPE_INTEGER, False, -500, 500)
            if YOffset_Last_keytype == '' : YOffset_Last_keytype = self.check_attribute_value(object_UID, lines_list, f'YOffset_Last{keytype}', ATTR_TYPE_INTEGER, False, 0, 500)

    #-------------------------------------------------------------------------------------------------
    def check_object_Panel(self, object_UID, lines_list):
        #--- check the data of a Panel object section which the lines are in the given lines list

        is_additional_panel = not(object_UID in ('Panel000', 'Organ')) # it is an additional panel, in addition to the Panel000 or Organ (old format) panel

        if self.new_panel_format:

            # required attributes (new panel format)
            self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, is_additional_panel)
            self.check_attribute_value(object_UID, lines_list, 'HasPedals', ATTR_TYPE_BOOLEAN, True)

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfGUIElements', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_UID}Element')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfGUIElements={ret} whereas {count} {object_UID}Element object(s) defined")

            # optional attributes (new panel format)
            self.check_attribute_value(object_UID, lines_list, 'Group', ATTR_TYPE_STRING, False)

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfImages', ATTR_TYPE_INTEGER, False, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_UID}Image')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfImages={ret} whereas {count} {object_UID}Image object(s) defined")

        elif is_additional_panel:  # additional panel in the old panel format (for the main panel, the non display metrics attributes are defined in the Organ object)

            # required attributes (old panel format, additional panel)
            self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, True)
            self.check_attribute_value(object_UID, lines_list, 'HasPedals', ATTR_TYPE_BOOLEAN, True)

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfCouplers', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Coupler{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                    self.check_attribute_value(object_UID, lines_list, f"Coupler{str(idx).zfill(3)}Manual", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}Coupler')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfCouplers={ret} whereas {count} {object_UID}Coupler object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfDivisionals', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Divisional{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                    self.check_attribute_value(object_UID, lines_list, f"Divisional{str(idx).zfill(3)}Manual", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}Divisional')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfDivisionals={ret} whereas {count} {object_UID}Divisional object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfDivisionalCouplers', ATTR_TYPE_INTEGER, True, 0, 8)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"DivisionalCoupler{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}DivisionalCoupler')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfDivisionalCouplers={ret} whereas {count} {object_UID}DivisionalCoupler object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfEnclosures', ATTR_TYPE_INTEGER, True, 0, 50)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Enclosure{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}Enclosure')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfEnclosures={ret} whereas {count} {object_UID}Enclosure object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfGenerals', ATTR_TYPE_INTEGER, True, 0, 99)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"General{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}General')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfGenerals={ret} whereas {count} {object_UID}General object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfImages', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_UID}Image')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfImages={ret} whereas {count} {object_UID}Image object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfLabels', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_UID}Label')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfLabels={ret} whereas {count} {object_UID}Label object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfManuals', ATTR_TYPE_INTEGER, True, 0, 16)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Manual{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfReversiblePistons', ATTR_TYPE_INTEGER, True, 0, 32)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"ReversiblePiston{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}ReversiblePiston')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfReversiblePistons={ret} whereas {count} {object_UID}ReversiblePiston object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfStops', ATTR_TYPE_INTEGER, True, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Stop{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                    self.check_attribute_value(object_UID, lines_list, f"Stop{str(idx).zfill(3)}Manual", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}Stop')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfStops={ret} whereas {count} {object_UID}Stop object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, 10)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Tremulant{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}Tremulant')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfTremulants={ret} whereas {count} {object_UID}Tremulant object(s) defined")

            # optional attributes (old panel format, additional panel)
            self.check_attribute_value(object_UID, lines_list, 'Group', ATTR_TYPE_STRING, False)

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSetterElements', ATTR_TYPE_INTEGER, False, 0, 8)
            if ret.isdigit() and int(ret) >= 0:
                count = self.objects_type_count(f'{object_UID}SetterElement')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfSetterElements={ret} whereas {count} {object_UID}SetterElement object(s) defined")

            ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfSwitches', ATTR_TYPE_INTEGER, False, 0, 999)
            if ret.isdigit() and int(ret) >= 0:
                for idx in range(1, int(ret)+1):
                    self.check_attribute_value(object_UID, lines_list, f"Switch{str(idx).zfill(3)}", ATTR_TYPE_OBJECT_REF, True)
                count = self.objects_type_count(f'{object_UID}Switch')
                if count != int(ret):
                    self.events_log_add(f"Error in {object_UID} : NumberOfSwitches={ret} whereas {count} {object_UID}Switch object(s) defined")


        # display metrics (common to old and new panel formats)

        # required attributes (panel display metrics)
        self.check_attribute_value(object_UID, lines_list, 'DispScreenSizeHoriz', ATTR_TYPE_PANEL_SIZE, True)
        self.check_attribute_value(object_UID, lines_list, 'DispScreenSizeVert', ATTR_TYPE_PANEL_SIZE, True)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_UID, lines_list, 'DispConsoleBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_UID, lines_list, 'DispKeyHorizBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_UID, lines_list, 'DispKeyVertBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopInsetBackgroundImageNum', ATTR_TYPE_INTEGER, True, 1, 64)
        self.check_attribute_value(object_UID, lines_list, 'DispControlLabelFont', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_UID, lines_list, 'DispShortcutKeyLabelFont', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_UID, lines_list, 'DispShortcutKeyLabelColour', ATTR_TYPE_COLOR, True)
        self.check_attribute_value(object_UID, lines_list, 'DispGroupLabelFont', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopCols', ATTR_TYPE_INTEGER, True, 2, 12)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopRows', ATTR_TYPE_INTEGER, True, 1, 20)
        cols_offset = self.check_attribute_value(object_UID, lines_list, 'DispDrawstopColsOffset', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispPairDrawstopCols', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispExtraDrawstopRows', ATTR_TYPE_INTEGER, True, 0, 99)
        self.check_attribute_value(object_UID, lines_list, 'DispExtraDrawstopCols', ATTR_TYPE_INTEGER, True, 0, 40)
        self.check_attribute_value(object_UID, lines_list, 'DispButtonCols', ATTR_TYPE_INTEGER, True, 1, 32)
        self.check_attribute_value(object_UID, lines_list, 'DispExtraButtonRows', ATTR_TYPE_INTEGER, True, 0, 99)
        extra_pedal_buttons = self.check_attribute_value(object_UID, lines_list, 'DispExtraPedalButtonRow', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispButtonsAboveManuals', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispExtraDrawstopRowsAboveExtraButtonRows', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispTrimAboveManuals', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispTrimBelowManuals', ATTR_TYPE_BOOLEAN, True)
        self.check_attribute_value(object_UID, lines_list, 'DispTrimAboveExtraRows', ATTR_TYPE_BOOLEAN, True)

        # optional attributes (panel display metrics)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopWidth', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopHeight', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_UID, lines_list, 'DispDrawstopOuterColOffsetUp', ATTR_TYPE_BOOLEAN, True if cols_offset == 'Y' else False)
        self.check_attribute_value(object_UID, lines_list, 'DispExtraPedalButtonRowOffset', ATTR_TYPE_BOOLEAN, True if extra_pedal_buttons == 'Y' else False)
        self.check_attribute_value(object_UID, lines_list, 'DispExtraPedalButtonRowOffsetRight', ATTR_TYPE_BOOLEAN, False)
        self.check_attribute_value(object_UID, lines_list, 'DispPistonWidth', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_UID, lines_list, 'DispPistonHeight', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_UID, lines_list, 'DispEnclosureWidth', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_UID, lines_list, 'DispEnclosureHeight', ATTR_TYPE_INTEGER, False, 1, 150)
        self.check_attribute_value(object_UID, lines_list, 'DispPedalHeight', ATTR_TYPE_INTEGER, False, 1, 500)
        self.check_attribute_value(object_UID, lines_list, 'DispPedalKeyWidth', ATTR_TYPE_INTEGER, False, 1, 500)
        self.check_attribute_value(object_UID, lines_list, 'DispManualHeight', ATTR_TYPE_INTEGER, False, 1, 500)
        self.check_attribute_value(object_UID, lines_list, 'DispManualKeyWidth', ATTR_TYPE_INTEGER, False, 1, 500)

    #-------------------------------------------------------------------------------------------------
    def check_object_PanelElement(self, object_UID, lines_list):
        #--- check the data of a Panel Element object section which the lines are in the given lines list

        # required attributes
        type = self.check_attribute_value(object_UID, lines_list, 'Type', ATTR_TYPE_ELEMENT_TYPE, True)

        if type == 'Coupler':
            self.check_attribute_value(object_UID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_attribute_value(object_UID, lines_list, 'Coupler', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Coupler(object_UID, lines_list)
        elif type == 'Divisional':
            self.check_attribute_value(object_UID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_attribute_value(object_UID, lines_list, 'Divisional', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Divisional(object_UID, lines_list)
        elif type == 'DivisionalCoupler':
            self.check_attribute_value(object_UID, lines_list, 'DivisionalCoupler', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_DivisionalCoupler(object_UID, lines_list)
        elif type == 'Enclosure':
            self.check_attribute_value(object_UID, lines_list, 'Enclosure', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Enclosure(object_UID, lines_list)
        elif type == 'General':
            self.check_attribute_value(object_UID, lines_list, 'General', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_General(object_UID, lines_list)
        elif type == 'Label':
            self.check_object_Label(object_UID, lines_list)
        elif type == 'Manual':
            self.check_attribute_value(object_UID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Manual(object_UID, lines_list)
        elif type == 'ReversiblePiston':
            self.check_attribute_value(object_UID, lines_list, 'ReversiblePiston', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_ReversiblePiston(object_UID, lines_list)
        elif type == 'Stop':
            self.check_attribute_value(object_UID, lines_list, 'Manual', ATTR_TYPE_OBJECT_REF, True)
            self.check_attribute_value(object_UID, lines_list, 'Stop', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Stop(object_UID, lines_list)
        elif type == 'Swell':
            self.check_object_Enclosure(object_UID, lines_list)
        elif type == 'Switch':
            self.check_attribute_value(object_UID, lines_list, 'Switch', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Switch(object_UID, lines_list)
        elif type == 'Tremulant':
            self.check_attribute_value(object_UID, lines_list, 'Tremulant', ATTR_TYPE_OBJECT_REF, True)
            self.check_object_Tremulant(object_UID, lines_list)
        else:
            self.check_object_SetterElement(object_UID, lines_list, type)

    #-------------------------------------------------------------------------------------------------
    def check_object_PanelOther(self, object_UID, lines_list):
        #--- check the data of an other kind of Panel object section (Panel999Coupler999, Panel999Divisional999, ...) which the lines are in the given lines list

        # get the object type from the object ID (for example Coupler from Panel999Coupler999)
        HW_object_type_str = object_UID[8:-3]
        object_type_plur = object_UID[8:-3] + 's' if HW_object_type_str != 'Switch' else object_UID[8:-3] + 'es'

        # check the attributes of the object depending on the object type
        if HW_object_type_str == 'Coupler':
            self.check_object_Coupler(object_UID, lines_list)
        elif HW_object_type_str == 'Divisional':
            self.check_object_Divisional(object_UID, lines_list)
        elif HW_object_type_str == 'DivisionalCoupler':
            self.check_object_DivisionalCoupler(object_UID, lines_list)
        elif HW_object_type_str == 'Enclosure':
            self.check_object_Enclosure(object_UID, lines_list)
        elif HW_object_type_str == 'General':
            self.check_object_General(object_UID, lines_list)
        elif HW_object_type_str == 'Image':
            self.check_object_Image(object_UID, lines_list)
        elif HW_object_type_str == 'Label':
            self.check_object_Label(object_UID, lines_list)
        elif HW_object_type_str == 'ReversiblePiston':
            self.check_object_ReversiblePiston(object_UID, lines_list)
        elif HW_object_type_str == 'SetterElement':
            self.check_object_SetterElement(object_UID, lines_list)
        elif HW_object_type_str == 'Stop':
            self.check_object_Stop(object_UID, lines_list)
        elif HW_object_type_str == 'Switch':
            self.check_object_Switch(object_UID, lines_list)
        elif HW_object_type_str == 'Tremulant':
            self.check_object_Tremulant(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Piston(self, object_UID, lines_list):
        #--- check the data of a Piston object section which the lines are in the given lines list

        # required attributes
        ret = self.check_attribute_value(object_UID, lines_list, 'ObjectType', ATTR_TYPE_PISTON_TYPE, True)
        self.check_attribute_value(object_UID, lines_list, 'ManualNumber', ATTR_TYPE_OBJECT_REF, ret in ('STOP', 'COUPLER'))
        self.check_attribute_value(object_UID, lines_list, 'ObjectNumber', ATTR_TYPE_INTEGER, False, 1, 200)

        # a Piston has also the attributes of a Push Button
        self.check_object_PushButton(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_PushButton(self, object_UID, lines_list):
        #--- check the data of a Push Button object section which the lines are in the given lines list

        # a Push Button has only the attributes of a Button
        self.check_object_Button(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Rank(self, object_UID, lines_list):
        #--- check the data of a Rank object section which the lines are in the given lines list

        is_rank_obj = object_UID.startswith('Rank') # some mandatory attributes are not mandatory for objects which inherit the Rank attributes (like Stop)

        # required attributes
        self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, True)
        self.check_attribute_value(object_UID, lines_list, 'FirstMidiNoteNumber', ATTR_TYPE_INTEGER, is_rank_obj, 0, 256)
        self.check_attribute_value(object_UID, lines_list, 'WindchestGroup', ATTR_TYPE_OBJECT_REF, True)
        self.check_attribute_value(object_UID, lines_list, 'Percussive', ATTR_TYPE_BOOLEAN, True)

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'AmplitudeLevel', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_UID, lines_list, 'Gain', ATTR_TYPE_FLOAT, False, -120, 40)
        self.check_attribute_value(object_UID, lines_list, 'PitchTuning', ATTR_TYPE_FLOAT, False, -1200, 1200)
        self.check_attribute_value(object_UID, lines_list, 'TrackerDelay', ATTR_TYPE_INTEGER, False, 0, 10000)
        self.check_attribute_value(object_UID, lines_list, 'HarmonicNumber', ATTR_TYPE_FLOAT, False, 1, 1024)
        self.check_attribute_value(object_UID, lines_list, 'PitchCorrection', ATTR_TYPE_FLOAT, False, -1200, 1200)
        self.check_attribute_value(object_UID, lines_list, 'MinVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_UID, lines_list, 'MaxVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)
        self.check_attribute_value(object_UID, lines_list, 'AcceptsRetuning', ATTR_TYPE_BOOLEAN, False)

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfLogicalPipes', ATTR_TYPE_INTEGER, is_rank_obj, 1, 192)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):  # Pipe999xxx attributes
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}', ATTR_TYPE_PIPE_WAVE, True)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Percussive', ATTR_TYPE_BOOLEAN, False)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}AmplitudeLevel', ATTR_TYPE_FLOAT, False, 0, 1000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Gain', ATTR_TYPE_FLOAT, False, -120, 40)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}PitchTuning', ATTR_TYPE_FLOAT, False, -1200, 1200)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}TrackerDelay', ATTR_TYPE_FLOAT, False, 0, 10000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}LoadRelease', ATTR_TYPE_BOOLEAN, False)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}AttackVelocity', ATTR_TYPE_INTEGER, False, 0, 127)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}MaxTimeSinceLastRelease', ATTR_TYPE_INTEGER, False, -1, 100000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}IsTremulant', ATTR_TYPE_INTEGER, False, -1, 1)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}MaxKeyPressTime', ATTR_TYPE_INTEGER, False, -1, 100000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}AttackStart', ATTR_TYPE_INTEGER, False, 0, 158760000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}CuePoint', ATTR_TYPE_INTEGER, False, -1, 158760000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}ReleaseEnd', ATTR_TYPE_INTEGER, False, -1, 158760000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}HarmonicNumber', ATTR_TYPE_FLOAT, False, 1, 1024)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}MIDIKeyNumber', ATTR_TYPE_INTEGER, False, -1, 127)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}PitchCorrection', ATTR_TYPE_FLOAT, False, -1200, 1200)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}AcceptsRetuning', ATTR_TYPE_BOOLEAN, False)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}WindchestGroup', ATTR_TYPE_OBJECT_REF, False)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}MinVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}MaxVelocityVolume', ATTR_TYPE_FLOAT, False, 0, 1000)

                ret1 = self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}LoopCount', ATTR_TYPE_INTEGER, False, 1, 100)
                if ret1.isdigit():
                    for idx1 in range(1, int(ret1)+1):  # Pipe999Loop999xxx attributes
                        ret = self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Loop{str(idx1).zfill(3)}Start', ATTR_TYPE_INTEGER, False, 0, 158760000)
                        loop_start = int(ret) if ret.isdigit() else 1
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Loop{str(idx1).zfill(3)}End', ATTR_TYPE_INTEGER, False, loop_start + 1, 158760000)

                ret1 = self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}AttackCount', ATTR_TYPE_INTEGER, False, 1, 100)
                if ret1.isdigit():
                    for idx1 in range(1, int(ret1)+1):  # Pipe999Attack999xxx attributes
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}', ATTR_TYPE_FILE_NAME, True)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}LoadRelease', ATTR_TYPE_BOOLEAN, False)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}AttackVelocity', ATTR_TYPE_INTEGER, False, 0, 127)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}MaxTimeSinceLastRelease', ATTR_TYPE_INTEGER, False, -1, 100000)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}IsTremulant', ATTR_TYPE_INTEGER, False, -1, 1)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}MaxKeyPressTime', ATTR_TYPE_INTEGER, False, -1, 100000)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}AttackStart', ATTR_TYPE_INTEGER, False, 0, 158760000)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}CuePoint', ATTR_TYPE_INTEGER, False, -1, 158760000)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}ReleaseEnd', ATTR_TYPE_INTEGER, False, -1, 158760000)

                        ret2 = self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}LoopCount', ATTR_TYPE_INTEGER, False, 1, 100)
                        if ret2.isdigit():
                            for idx2 in range(1, int(ret2)+1):  # Pipe999Attack999Loop999xxx attributes
                                ret = self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}Loop{str(idx2).zfill(3)}Start', ATTR_TYPE_INTEGER, True, 0, 158760000)
                                loop_start = int(ret) if ret.isdigit() else 1
                                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Attack{str(idx1).zfill(3)}Loop{str(idx2).zfill(3)}End', ATTR_TYPE_INTEGER, True, loop_start + 1, 158760000)

                ret1 = self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}ReleaseCount', ATTR_TYPE_INTEGER, False, 1, 100)
                if ret1.isdigit():
                    for idx1 in range(1, int(ret1)+1):  # Pipe999Release999xxx attributes
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}', ATTR_TYPE_FILE_NAME, True)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}IsTremulant', ATTR_TYPE_INTEGER, False, -1, 1)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}MaxKeyPressTime', ATTR_TYPE_INTEGER, False, -1, 100000)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}CuePoint', ATTR_TYPE_INTEGER, False, -1, 158760000)
                        self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}Release{str(idx1).zfill(3)}ReleaseEnd', ATTR_TYPE_INTEGER, False, -1, 158760000)

                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}LoopCrossfadeLength', ATTR_TYPE_INTEGER, False, 0, 120)
                self.check_attribute_value(object_UID, lines_list, f'Pipe{str(idx).zfill(3)}ReleaseCrossfadeLength', ATTR_TYPE_INTEGER, False, 0, 120)

    #-------------------------------------------------------------------------------------------------
    def check_object_ReversiblePiston(self, object_UID, lines_list):
        #--- check the data of a Reversible Piston object section which the lines are in the given lines list

        # unkown expected attributes...
        pass

     #-------------------------------------------------------------------------------------------------
    def check_object_SetterElement(self, object_UID, lines_list, type = ''):
        #--- check the data of a Setter Element object section which the lines are in the given lines list

        # required attributes
        if type == '':
            # type not provided by the caller, recover it from the object lines list
            type = self.check_attribute_value(object_UID, lines_list, 'Type', ATTR_TYPE_ELEMENT_TYPE, True)

        if type == 'CrescendoLabel':
            self.check_object_Label(object_UID, lines_list)
        elif type in ('CrescendoA', 'CrescendoB', 'CrescendoC', 'CrescendoD'):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('CrescendoPrev', 'CrescendoNext', 'CrescendoCurrent'):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('Current', 'Full', 'GC'):
            self.check_object_Button(object_UID, lines_list)
        elif type[:7] == "General" and len(type) == 9 and type[7:9].isdigit() and int(type[7:9]) in range(1, 51):
            self.check_object_Button(object_UID, lines_list)
        elif type == 'GeneralLabel':
            self.check_object_Label(object_UID, lines_list)
        elif type in ('GeneralPrev', 'GeneralNext', 'Home', 'Insert', 'Delete'):
            self.check_object_Button(object_UID, lines_list)
        elif type[:1] == "L" and len(type) == 2 and type[1:2].isdigit() and int(type[1:2]) in range(0, 10):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('M100', 'M10', 'M1', 'P1', 'P10', 'P100'):
            self.check_object_Button(object_UID, lines_list)
        elif type == 'PitchLabel':
            self.check_object_Label(object_UID, lines_list)
        elif type in ('PitchM100', 'PitchM10', 'PitchM1', 'PitchP1', 'PitchP10', 'PitchP100'):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('Prev', 'Next', 'Set'):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('Regular', 'Scope', 'Scoped', 'Save'):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('SequencerLabel', 'TemperamentLabel'):
            self.check_object_Label(object_UID, lines_list)
        elif type in ('TemperamentPrev', 'TemperamentNext'):
            self.check_object_Button(object_UID, lines_list)
        elif type in ('TransposeDown', 'TransposeUp'):
            self.check_object_Button(object_UID, lines_list)
        elif type == 'TransposeLabel':
            self.check_object_Label(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Stop(self, object_UID, lines_list):
        #--- check the data of a Stop object section which the lines are in the given lines list

        is_stop_obj = object_UID.startswith('Stop') # some mandatory attributes are not mandatory for objects which inherit the Stop attributes

        # optional attribute
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfRanks', ATTR_TYPE_INTEGER, False, 0, 999)
        if ret == '' or not ret.isdigit():
            # number of ranks not defined or not a number
            nb_ranks = 0
        else:
            nb_ranks = int(ret)

        # required attributes
        self.check_attribute_value(object_UID, lines_list, 'FirstAccessiblePipeLogicalKeyNumber', ATTR_TYPE_INTEGER, is_stop_obj, 1, 128)
        self.check_attribute_value(object_UID, lines_list, 'FirstAccessiblePipeLogicalPipeNumber', ATTR_TYPE_INTEGER, nb_ranks == 0, 1, 192)

        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfAccessiblePipes', ATTR_TYPE_INTEGER, True, 1, 192)
        nb_pipes = int(ret) if ret.isdigit() else 192

        # optional attributes
        if nb_ranks > 0:
            for idx in range(1, nb_ranks+1):
                self.check_attribute_value(object_UID, lines_list, f'Rank{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)
                self.check_attribute_value(object_UID, lines_list, f'Rank{str(idx).zfill(3)}FirstPipeNumber', ATTR_TYPE_INTEGER, False, 1, nb_pipes)
                self.check_attribute_value(object_UID, lines_list, f'Rank{str(idx).zfill(3)}PipeCount', ATTR_TYPE_INTEGER, False, 0, nb_pipes)
                self.check_attribute_value(object_UID, lines_list, f'Rank{str(idx).zfill(3)}FirstAccessibleKeyNumber', ATTR_TYPE_INTEGER, False, 1, nb_pipes)
        elif nb_ranks == 0:
            # number of ranks set at 0, the Stop must contain rank attributes
            self.check_object_Rank(object_UID, lines_list)

        # a Stop has also the attributes of a Drawstop
        self.check_object_DrawStop(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Switch(self, object_UID, lines_list):
        #--- check the data of a Switch object section which the lines are in the given lines list

        # a Switch has only the attributes of a Drawstop
        self.check_object_DrawStop(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_Tremulant(self, object_UID, lines_list):
        #--- check the data of a Tremulant object section which the lines are in the given lines list

        # optional attributes
        ret = self.check_attribute_value(object_UID, lines_list, 'TremulantType', ATTR_TYPE_TREMULANT_TYPE, False)
        is_synth = (ret == 'Synth')
        self.check_attribute_value(object_UID, lines_list, 'Period', ATTR_TYPE_INTEGER, is_synth, 32, 44100)
        self.check_attribute_value(object_UID, lines_list, 'StartRate', ATTR_TYPE_INTEGER, is_synth, 1, 100)
        self.check_attribute_value(object_UID, lines_list, 'StopRate', ATTR_TYPE_INTEGER, is_synth, 1, 100)
        self.check_attribute_value(object_UID, lines_list, 'AmpModDepth', ATTR_TYPE_INTEGER, is_synth, 1, 100)

        # a Tremulant has also the attributes of a Drawstop
        self.check_object_DrawStop(object_UID, lines_list)

    #-------------------------------------------------------------------------------------------------
    def check_object_WindchestGroup(self, object_UID, lines_list):
        #--- check the data of a WindChest Group object section which the lines are in the given lines list

        # required attributes
        max = self.objects_type_count('Enclosure')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfEnclosures', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Enclosure{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        max = self.objects_type_count('Tremulant')
        ret = self.check_attribute_value(object_UID, lines_list, 'NumberOfTremulants', ATTR_TYPE_INTEGER, True, 0, max)
        if ret.isdigit():
            for idx in range(1, int(ret)+1):
                self.check_attribute_value(object_UID, lines_list, f'Tremulant{str(idx).zfill(3)}', ATTR_TYPE_OBJECT_REF, True)

        # optional attributes
        self.check_attribute_value(object_UID, lines_list, 'Name', ATTR_TYPE_STRING, False)

    #-------------------------------------------------------------------------------------------------
    def check_attribute_value(self, object_UID, lines_list, attribute_name, attribute_value_type, required_attribute, attribute_value_min=0, attribute_value_max=0):
        #--- check if the given attribute name is present in the given object lines list, and if its value is correct for its value type and min/max values
        #--- the min and max values are ignored if max <= min. The given lines list is considered to be sorted
        #--- returns the value of the attribute if it has been found and without error, else return ''

        # check that the given max value is higher or equal to the min value (this should never happen)
        if attribute_value_max < attribute_value_max:
            self.events_log_add(f"INTERNAL ERROR : check_attribute_value called with max < min for {object_UID} / {attribute_name} : min={attribute_value_min}, max={attribute_value_max}")
            return ''

        # recover the value of the attribute to check
        (attr_value_str, attr_idx) = self.object_get_attribute_value(lines_list, attribute_name, True)

        if attr_idx != -1:
            # the attribute has been found
            self.check_nb_attr += 1

            line = lines_list[attr_idx]

            # check the attribute value according to the given type

            if attribute_value_type == ATTR_TYPE_INTEGER:
                if (not attr_value_str.lstrip("-+").isdigit() or
                    ((int(attr_value_str) < attribute_value_min or int(attr_value_str) > attribute_value_max))):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value must be an integer in the range [{attribute_value_min} - {attribute_value_max}]")

            elif attribute_value_type == ATTR_TYPE_FLOAT:
                if (not(attr_value_str.lstrip("-+").replace('.', '', 1).isdigit()) or
                    ((float(attr_value_str) < attribute_value_min or float(attr_value_str) > attribute_value_max))):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value must be an integer or decimal in the range [{attribute_value_min} - {attribute_value_max}]")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_BOOLEAN:
                if attr_value_str.upper() not in ('Y', 'N'):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value must be Y or N (boolean attribute)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_STRING:
                pass # nothing to check in case of string value

            elif attribute_value_type == ATTR_TYPE_COLOR:
                if (not(attr_value_str.upper() in ('BLACK', 'BLUE', 'DARK BLUE', 'GREEN', 'DARK GREEN', 'CYAN', 'DARK CYAN', 'RED', 'DARK RED',
                                               'MAGENTA', 'DARK MAGENTA', 'YELLOW', 'DARK YELLOW', 'LIGHT GREY', 'DARK GREY', 'WHITE', 'BROWN')) and
                    not(len(attr_value_str) == 7 and attr_value_str[0] == '#' and attr_value_str[1:].isalnum())):  # check of the HTML format #RRGGBB
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid color (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_FONT_SIZE:
                if (not(attr_value_str.upper() in ('SMALL', 'NORMAL', 'LARGE')) and
                    not(attr_value_str.isdigit() and int(attr_value_str) >= 1 and int(attr_value_str) <= 50)):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid font size (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_PANEL_SIZE:
                if (not(attr_value_str.upper() in ('SMALL', 'MEDIUM', 'MEDIUM LARGE', 'LARGE')) and
                    not(attr_value_str.isdigit() and int(attr_value_str) >= 100 and int(attr_value_str) <= 4000)):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid panel size (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_OBJECT_REF:  # for example Switch002=12 or ManualNumber=2 or Stop003Manual=2 or Pipe015WindchestGroup=1
                if attribute_name[-3:].isdigit():
                    attribute_name = attribute_name[:-3]   # remove the three digits at the end of the attribute name to get the object name

                if attribute_name[-6:] == 'Number':
                    attribute_name = attribute_name[:-6]   # remove the 'Number' string at the end, used in General and Piston objects
                elif attribute_name[-6:] == 'Manual':
                    attribute_name = 'Manual'         # keep only the 'Manual' string, used in General object
                elif attribute_name[-14:] == 'WindchestGroup':
                    attribute_name = 'WindchestGroup' # keep only the 'WindchestGroup' string, used in Rank object

                attr_value_str = attr_value_str.lstrip("+-") # remove possible + or - at the beginning of the value, used in General or Divisional objects

                if not(attribute_name + attr_value_str.zfill(3)) in self.odf_objects_dic:
                    self.events_log_add(f"Error in {object_UID} / {line} : the object {attribute_name + attr_value_str.zfill(3)} does not exist")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_ELEMENT_TYPE:
                if (not(attr_value_str in ('Coupler', 'Divisional', 'DivisionalCoupler', 'Enclosure', 'General', 'Label', 'Manual', 'ReversiblePiston', 'Stop', 'Swell',
                                      'Switch', 'Tremulant', 'CrescendoA', 'CrescendoB', 'CrescendoC', 'CrescendoD', 'CrescendoPrev', 'CrescendoNext', 'CrescendoCurrent',
                                      'Current', 'Full', 'GC', 'GeneralLabel', 'GeneralPrev', 'GeneralNext', 'Home', 'Insert', 'Delete', 'M100', 'M10', 'M1', 'P1', 'P10', 'P100',
                                      'PitchLabel', 'PitchP1', 'PitchP10', 'PitchP100', 'PitchM1', 'PitchM10', 'PitchM100', 'Prev', 'Next', 'Set', 'Regular', 'Scope', 'Scoped',
                                      'Save', 'SequencerLabel', 'TemperamentLabel', 'TemperamentPrev', 'TemperamentNext', 'TransposeDown', 'TransposeUp', 'TransposeLabel')) and
                    not(attr_value_str[0] == 'L' and attr_value_str[1].isdigit() and int(attr_value_str[1]) in range(0, 10)) and
                    not(attr_value_str[:14] == 'CrescendoLabel' and attr_value_str[14:].isdigit() and int(attr_value_str[14:]) in range(1, 33)) and
                    not(attr_value_str[:7] == 'General' and attr_value_str[7:].isdigit() and int(attr_value_str[7:]) in range(1, 51))):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid panel element type (look at the help)")
                    attr_value_str = ''
                pass

            elif attribute_value_type == ATTR_TYPE_COUPLER_TYPE:
                if not(attr_value_str.upper() in ('NORMAL', 'BASS', 'MELODY')):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid coupler type (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_TREMULANT_TYPE:
                if not(attr_value_str.upper() in ('SYNTH', 'WAVE')):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid tremulant type (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_PISTON_TYPE:
                if not(attr_value_str.upper() in ('STOP', 'COUPLER', 'SWITCH', 'TREMULANT')):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid piston type (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_DRAWSTOP_FCT:
                if not(attr_value_str.upper() in ('INPUT', 'NOT', 'AND', 'XOR', 'NAND', 'NOR', 'OR')):
                    self.events_log_add(f"Error in {object_UID} / {line} : the assigned value is not a valid drawstop function (look at the help)")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_FILE_NAME:
                modif_path = attr_value_str.replace('\\', '/')
                if self.check_files_names and not os.path.isfile(os.path.dirname(self.odf_file_name) + '/' + modif_path):
                    self.events_log_add(f"Error in {object_UID} / {line} : file does not exist")
                    attr_value_str = ''

            elif attribute_value_type == ATTR_TYPE_PIPE_WAVE:
                if attr_value_str.upper()[-4:] == '.WAV':
                    modif_path = attr_value_str.replace('\\', '/')
                    if self.check_files_names and not os.path.isfile(os.path.dirname(self.odf_file_name) + '/' + modif_path):
                        self.events_log_add(f"Error in {object_UID} / {line} : file not found")
                        attr_value_str = ''
                elif attr_value_str[:4] == 'REF:':  # for example REF:001:005:007
                    if not (attr_value_str[5:7].isdigit and attr_value_str[7] == ':' and
                            attr_value_str[8:11].isdigit and attr_value_str[11] == ':' and
                            attr_value_str[12:15].isdigit and len(attr_value_str) == 15):
                        self.events_log_add(f"Error in {object_UID} / {line} : wrong pipe referencing, expected REF:999:999:999")
                        attr_value_str = ''
                elif attr_value_str != 'EMPTY':
                    self.events_log_add(f"Error in {object_UID} / {line} : wrong pipe definition")
                    attr_value_str = ''

             # remove the line of the found attribute, to know at the end of the object check which of its attributes have not been checked
            lines_list.pop(attr_idx)

        elif required_attribute:
            # the attribute has not been found and it is required
            self.events_log_add(f"Error in {object_UID} : the attribute {attribute_name} is expected, it is missing or misspelled")

        return attr_value_str

    #-------------------------------------------------------------------------------------------------
    def check_attributes_unicity(self, object_UID, lines_list):
        #--- check in the given object lines list if each attribute is unique

        # copy the attributes names of the given lines list in an attributes list
        attributes_list = []
        for line in lines_list:
            if self.is_line_with_attribute(line):
                (attr_name_str, attr_value_str) = line.split("=", 1)
                attributes_list.append(attr_name_str)

        # sort the attributes list
        attributes_list.sort()

        # check if there are consecutive names in the sorted list
        for i in range(0, len(attributes_list) - 1):
            if attributes_list[i] == attributes_list[i+1]:
                self.events_log_add(f"Error in {object_UID} : the attribute {attributes_list[i]} is defined more than once")

#-------------------------------------------------------------------------------------------------
class C_HW2GO():
    #--- class to manage the conversion of a Hauptwerk ODF in a GrandOrgue ODF

    HW_ODF_file_name_str = ''  # name of the loaded Hauptwerk ODF

    HW_ODF_dic = {}  # dictionary in which are stored the data of the loaded Hauptwerk ODF file (XML file)
                      # it has the following structure with three nested dictionaries :
                      #   {ObjectType:                      -> string, for example _General, KeyImageSet, DisplayPage
                      #       {ObjectID:                    -> integer, from 1 to 999999, recovered from the HW ODF objects ID when possible, else set by increment
                      #           {Attribute: Value, ...},  -> string: string
                      #        ...
                      #       },
                      #       ...
                      #    ...
                      #   }
                      # the ObjectUID (unique ID) is a string made by the concatenation of the ObjectType and the ObjectID on 6 digits, for example DisplayPage000006
                      # exception : the ObjectType _General has the ObjectUID _General

    GO_ODF_dic = {}  # dictionary in which are stored the data of the GrandOrgue ODF built from the Hauptwerk ODF dictionary
                      # it has the following structure with two nested dictionaries :
                      #   {ObjectUID:                   -> string, for example Organ, Panel001, Rank003
                      #       {Attribute: Value, ...}   -> string: string or integer if number / dimension / code
                      #    ...
                      #   }

    HW_ODF_attr_dic = {} # dictionary which contains the definition of the various HW object types and their attributes (loaded from the file HwObjectsAttributesDict.txt)
                          # it has the following structure with two nested dictionaries :
                          #   {ObjectType:                                  -> string, for example _General, KeyImageSet, DisplayPage
                          #       {AttributeLetter: AttributeFullName, ...} -> string: string
                          #    ...
                          #   }

    GO_objects_type_nb_dic = {}  # dictionary with GO objects types names as keys and the associated number of these objects types as integer values

    HW_packages_id_list = []  # list containing the present packages ID (integer) in the sample set of the loaded Hauptwerk ODF

    HW_default_display_page_id = 0  # ID of the HW default display page (which is displayed by default on organ loading and will be the GO Panel000)
    HW_console_display_page_id = 0  # ID of the HW console display page (which contains the displayed keyboards, can be different from the default display page)

    events_log_list = []    # list of events logs (errors or messages resulting from the conversion or files operations)


    #-------------------------------------------------------------------------------------------------
    def HW_ODF_load_from_file(self, file_name_str):
        # fill the Hauptwerk ODF dictionary from the data of the given Hauptwerk ODF XML file
        # return True or False whether the operation has succeeded or not

        """
        the considered Hauptwerk ODF XML syntax is :

        <Hauptwerk FileFormat="Organ" FileFormatVersion="xxxxxx">
            <ObjectList ObjectType="ObjectTypeName">
                <"ObjectTypeName">
                    <"Attribute1">Value</"Attribute1">
                    <"Attribute2">Value</"Attribute2">
                    ...
                </"ObjectTypeName">
                ...
                <o>                    -> compressed format
                    <a>Value</a>
                    <b>Value</b>
                    ...
                </o>
                ...
            </ObjectList>
               ...
        </Hauptwerk>

        the attributes letters are converted to attributes full name thanks to the dictionary HW_ODF_attr_dic
        """

        # check the extension of the given file name
        filename_str, file_extension_str = os.path.splitext(file_name_str)
        if file_extension_str != '.Organ_Hauptwerk_xml':
            self.events_log_add(f'ERROR : The file "{file_name_str}" does not have the expected extension .Organ_Hauptwerk_xml')
            return False

        # check the existence of the given file name
        if not(os.path.isfile(file_name_str)):
            self.events_log_add(f'ERROR : The file "{file_name_str}" does not exist')
            return False

        # load the dictionnary HW_ODF_attr_dic if not already loaded
        if not self.HW_ODF_attr_dic_file_load():
            # error occurred while loading the dictionary
            return False

        # clear the content of the dictionary HW_ODF_dic
        self.HW_ODF_dic.clear()

        # load the content of the HW XML file as an elements tree
        HW_ODF_xml_tree = etree.parse(file_name_str)

        # check that it is actually an Hauptwerk ODF and recover the file format version
        HW_xml_id_tag_str = HW_ODF_xml_tree.xpath("/Hauptwerk")
        HW_file_format_str = HW_xml_id_tag_str[0].get("FileFormat")
        HW_file_format_version_str = HW_xml_id_tag_str[0].get("FileFormatVersion")
        if HW_file_format_str != 'Organ':
            # it is not an ODF
            self.events_log_add(f'ERROR : The file "{file_name_str}" is not a supported Hauptwerk organ definition file')
            return False

        object_type_nb_int = 0  # total number of object types found
        object_elem_nb_int = 0  # total number of object elements found
        object_attr_nb_int = 0  # total number of object attributes found
        for xml_object_type in HW_ODF_xml_tree.xpath("/Hauptwerk/ObjectList"):
            # parse the object types defined in the XML file (in the tags <ObjectList ObjectType="xxxx">)
            object_type_nb_int += 1

            # recover the name of the current object type
            HW_object_type_str = xml_object_type.get("ObjectType")

            # create an entry in the HW dictionary for the current object type
            object_type_dic = self.HW_ODF_dic[HW_object_type_str] = {}

            if HW_object_type_str in self.HW_ODF_attr_dic.keys():
                # the current object type is defined in the HW attributes dictionary
                # get the dictionary defining the attributes of the current object type
                object_type_attr_dic = self.HW_ODF_attr_dic[HW_object_type_str]
                # recover the name of the attribute of the object elements of the current object type which define the ID of each element, if it exists
                object_id_attr_name_str = object_type_attr_dic['IDattr']

                object_id_counter_int = 0  # ID which can be assigned to the current object element inside the current object type if it has not an ID defined in the attributes
                for xml_object_element in xml_object_type:
                    # parse the object elements defined in the current object type
                    object_elem_nb_int += 1
                    object_id_counter_int += 1
                    object_id_int = 0

                    # create a new object element dictionary
                    object_dic = {}

                    # add at the beginning of the current object element dictionary some custom attributes used for the GO ODF building
                    object_dic['_HW_uid'] = ''  # Unique ID of the HW object
                    object_dic['_GO_uid'] = ''  # Unique ID of the corresponding built GO object
                    object_dic['_parents'] = []   # list of the parent HW objects dictionaries
                    object_dic['_children'] = []  # list of the children HW objects dictionaries

                    for xml_object_attribute in xml_object_element:
                        # parse the attributes defined in the current object element
                        object_attr_nb_int += 1
                        attribute_name_str = xml_object_attribute.tag
                        attribute_value_str = xml_object_attribute.text

                        if attribute_value_str != '' and attribute_value_str != None:
                            # the attributes with an empty or undefined value are ignored
                            if len(attribute_name_str) <= 2:
                                # the attribute name is defined by a tag of one or two characters (this is the Hauptwerk XML compressed format)
                                # recover the attribute long name corresponding to this tag
                                try:
                                    attribute_name_str = object_type_attr_dic[attribute_name_str]
                                except:
                                    # no attribute long name known
                                    attribute_name_str = attribute_name_str + '???'

                            # add the current attribute name and value to the current object
                            object_dic[attribute_name_str] = attribute_value_str

                            if object_id_int == 0 and object_id_attr_name_str != '' and attribute_name_str == object_id_attr_name_str:
                                # the current attribute is the attribute which contains the ID of the object in the current object type
                                if not attribute_value_str.isnumeric():
                                    self.events_log_add(f'ERROR : attribute {attribute_name_str}={attribute_value_str} has not a numeric value in the object {HW_object_type_str} #{object_id_counter_int}')
                                else:
                                    object_id_int = int(attribute_value_str)

                    if object_id_int == 0:
                        # no object ID recovered from the attributes
                        if object_id_attr_name_str != '':
                            # the object should have had an ID attribute
                            self.events_log_add(f'ERROR : attribute {object_id_attr_name_str} with integer value not found in the object {HW_object_type_str} #{object_id_counter_int}')
                        # use as object ID the objects counter
                        object_id_int = object_id_counter_int

                    # store in the object its UID (unique ID)
                    if HW_object_type_str == '_General':
                        object_dic['_HW_uid'] = '_General'
                    else:
                        object_dic['_HW_uid'] = HW_object_type_str + str(object_id_int).zfill(6)

                    if object_id_int in object_type_dic.keys():
                        self.events_log_add(f'WARNING: HW object {object_dic["_HW_uid"]} has an ID which is not unique !')

                    # add the object dictionary to the current object type dictionary
                    object_type_dic[object_id_int] = object_dic

            else:
                self.events_log_add(f'INTERNAL ERROR : object type {HW_object_type_str} unknown in the HW attributes dictionary')

        self.events_log_add(f'Hauptwerk ODF loaded "{file_name_str}"')
        self.events_log_add(f'{object_attr_nb_int} attributes among {object_elem_nb_int} objects among {object_type_nb_int} object types')

        self.HW_ODF_file_name_str = file_name_str

        return True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_attr_dic_file_load(self):
        # load the Hauptwerk attributes dictionary from the file HwObjectsAttributesDict.txt (if it is present and there is no error)
        # return True or False whether the operation has succeeded or not

        if len(self.HW_ODF_attr_dic) == 0:
            # the dictionary has not been loaded yet

            file_name_str = os.path.dirname(__file__) + '/HwObjectsAttributesDict.txt'

            try:
                with open(file_name_str, 'r') as f:
                    self.HW_ODF_attr_dic = eval(f.read())
                    return True
            except OSError as err:
                # it has not be possible to open the file
                self.events_log_add(f'ERROR : Cannot open the file "{file_name_str}" : {err}')
            except SyntaxError as err:
                # syntax error in the dictionary structure which is in the file
                self.events_log_add(f'ERROR : Syntax error in the file "{file_name_str}" : {err}')
            except:
                # other error
                self.events_log_add(f'ERROR : Error while opening the file "{file_name_str}"')

            return False

        else:
            return True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_do_links_between_objects(self):
        # set in the Hauptwerk ODF dictionary the relationships (parent, children) between the various objects
        # add in the objects of the HW_ODF_dic the attributes "_parents" and "_children" with as value the list of the respective parent or child objects

        HW_general_object_dic = None
        HW_object_type_str = '_General'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'OrganInfo_InstallationPackageID', 'RequiredInstallationPackage', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SpecialObjects_DefaultDisplayPageID', 'DisplayPage', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SpecialObjects_MasterCaptureSwitchID', 'Switch', TO_CHILD)
                HW_general_object_dic = HW_object_dic
        if HW_general_object_dic == None:
            self.events_log_add(f'ERROR : no _General object defined in the Hauptwerk ODF')
            return False

        HW_object_type_str = 'DivisionInput'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DivisionID', 'Division', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'Keyboard'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'KeyGen_DisplayPageID', 'DisplayPage', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'KeyGen_KeyImageSetID', 'KeyImageSet',  TO_CHILD)
                # link the keyboard to its division
                HW_division_dic = self.HW_ODF_get_object_dic_by_ref_id('Division', HW_object_dic, 'Hint_PrimaryAssociatedDivisionID')
                if HW_division_dic == None:
                    # find the division ID from the keyboard code, supposing to the following matching :
                    #     keyboard code 1 = division 1 = Pedal
                    #     keyboard code 2 = division 2 = Manual 1
                    #     keyboard code 3 = division 3 = Manual 2
                    #     ...
                    HW_division_dic = self.HW_ODF_get_object_dic_by_ref_id('Division', HW_object_dic, 'DefaultInputOutputKeyboardAsgnCode')
                if HW_division_dic != None:
                    self.HW_ODF_do_link_between_obj(HW_object_dic, HW_division_dic, TO_PARENT)

        HW_object_type_str = 'KeyAction'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SourceKeyboardID', 'Keyboard', TO_PARENT)
                if self.HW_ODF_get_attribute_value(HW_object_dic, 'DestDivisionID') != None:
                    # the key action destination is a division
                    self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DestDivisionID', 'Division', TO_CHILD)
                    # link directly the source keyboard to the division if there is no conditional switch
                    # this link may have been done already while processing the Keyboard objects above
                    HW_cond_switch_dic = self.HW_ODF_get_attribute_value(HW_object_dic, 'ConditionSwitchID')
                    if HW_cond_switch_dic == None:
                        HW_source_keyboard_dic = self.HW_ODF_get_object_dic_by_ref_id('Keyboard', HW_object_dic, 'SourceKeyboardID')
                        HW_dest_division_dic = self.HW_ODF_get_object_dic_by_ref_id('Division', HW_object_dic, 'DestDivisionID')
                        self.HW_ODF_do_link_between_obj(HW_source_keyboard_dic, HW_dest_division_dic, TO_PARENT)
                else:
                    # the key action destination is a keyboard
                    self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DestKeyboardID', 'Keyboard', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ConditionSwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'KeyboardKey'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'KeyboardID', 'Keyboard', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'KeyImageSet'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                for obj_attr_name_str in list(HW_object_dic.keys()):
                    if obj_attr_name_str.startswith('KeyShapeImageSetID'):
                        self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, obj_attr_name_str, 'ImageSet', TO_CHILD)

        HW_object_type_str = 'ImageSetElement'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ImageSetID', 'ImageSet', TO_PARENT)

        HW_object_type_str = 'TextInstance'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DisplayPageID', 'DisplayPage', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'TextStyleID', 'TextStyle', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'AttachedToImageSetInstanceID', 'ImageSetInstance', TO_CHILD)

        HW_object_type_str = 'Switch'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'Disp_ImageSetInstanceID', 'ImageSetInstance', TO_CHILD)
                # if the Switch is linked to an ImageSetInstance object, link it to the DisplayPage in which it is displayed
                HW_image_set_inst_dic = self.HW_ODF_get_object_dic_by_ref_id('ImageSetInstance', HW_object_dic, 'Disp_ImageSetInstanceID')
                if HW_image_set_inst_dic != None:
                    HW_display_page_dic = self.HW_ODF_get_object_dic_by_ref_id('DisplayPage', HW_image_set_inst_dic, 'DisplayPageID')
                    self.HW_ODF_do_link_between_obj(HW_object_dic, HW_display_page_dic, TO_PARENT)

        HW_object_type_str = 'SwitchLinkage'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SourceSwitchID', 'Switch', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DestSwitchID', 'Switch', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ConditionSwitchID', 'Switch', TO_PARENT)
                # make direct link between source and destination switches
                HW_source_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_object_dic, 'SourceSwitchID')
                HW_dest_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_object_dic, 'DestSwitchID')
                HW_cond_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_object_dic, 'ConditionSwitchID')
                if HW_source_switch_dic != None and HW_dest_switch_dic != None :
                    self.HW_ODF_do_link_between_obj(HW_source_switch_dic, HW_dest_switch_dic, TO_CHILD)
                    if HW_cond_switch_dic != None:
                        self.HW_ODF_do_link_between_obj(HW_cond_switch_dic, HW_dest_switch_dic, TO_CHILD)

        HW_object_type_str = 'SwitchExclusiveSelectGroupElement'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SwitchID', 'Switch', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'GroupID', 'SwitchExclusiveSelectGroup', TO_PARENT)

        HW_object_type_str = 'WindCompartment'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PressureOutputContinuousControlID', 'ContinuousControl', TO_PARENT)

        HW_object_type_str = 'WindCompartmentLinkage'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'FirstWindCompartmentID', 'WindCompartment', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SecondWindCompartmentID', 'WindCompartment', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ValveControllingContinuousControlID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ValveControllingSwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'Stop'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DivisionID', 'Division', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ControllingSwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'StopRank'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'StopID', 'Stop', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'RankID', 'Rank', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SwitchIDToSwitchToAlternateRank', 'Switch', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'AlternateRankID', 'Rank', TO_CHILD)

        HW_object_type_str = 'Combination'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ActivatingSwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'CombinationElement'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'CombinationID', 'Combination', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ControlledSwitchID', 'Switch', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'CapturedSwitchID', 'Switch', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'MemorySwitchID', 'Switch', TO_CHILD)

        HW_object_type_str = 'Pipe_SoundEngine01'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'RankID', 'Rank', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ControllingPalletSwitchID', 'Switch', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'WindSupply_SourceWindCompartmentID', 'WindCompartment', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'WindSupply_OutputWindCompartmentID', 'WindCompartment', TO_CHILD)

        HW_object_type_str = 'Pipe_SoundEngine01_Layer'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PipeID', 'Pipe_SoundEngine01', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'Main_AttackSelCriteria_ContinuousControlID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'Main_ReleaseSelCriteria_ContinuousControlID', 'ContinuousControl', TO_PARENT)

        HW_object_type_str = 'Pipe_SoundEngine01_AttackSample'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'LayerID', 'Pipe_SoundEngine01_Layer', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SampleID', 'Sample', TO_CHILD)

        HW_object_type_str = 'Pipe_SoundEngine01_ReleaseSample'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'LayerID', 'Pipe_SoundEngine01_Layer', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SampleID', 'Sample', TO_CHILD)

        HW_object_type_str = 'ContinuousControlStageSwitch'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ContinuousControlID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ControlledSwitchID', 'Switch', TO_CHILD)

        HW_object_type_str = 'ContinuousControlLinkage'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SourceControlID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DestControlID', 'ContinuousControl', TO_CHILD)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ConditionSwitchID', 'Switch', TO_PARENT)

        HW_object_type_str = 'ContinuousControl'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ImageSetInstanceID', 'ImageSetInstance', TO_CHILD)
                # if the ContinuousControl is linked to an ImageSetInstance object, link it to the DisplayPage in which it is displayed
                HW_image_set_inst_dic = self.HW_ODF_get_object_dic_by_ref_id('ImageSetInstance', HW_object_dic, 'ImageSetInstanceID')
                if HW_image_set_inst_dic != None:
                    HW_display_page_dic = self.HW_ODF_get_object_dic_by_ref_id('DisplayPage', HW_image_set_inst_dic, 'DisplayPageID')
                    self.HW_ODF_do_link_between_obj(HW_object_dic, HW_display_page_dic, TO_PARENT)

        HW_object_type_str = 'ContinuousControlImageSetStage'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ImageSetID', 'ImageSet', TO_PARENT)

        HW_object_type_str = 'ContinuousControlDoubleLinkage'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'FirstSourceControl_UID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'SecondSourceControl_UID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DestControl_UID', 'ContinuousControl', TO_CHILD)

        HW_object_type_str = 'Enclosure'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ShutterPositionContinuousControlID', 'ContinuousControl', TO_PARENT)

        HW_object_type_str = 'EnclosurePipe'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'EnclosureID', 'Enclosure', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PipeID', 'Pipe_SoundEngine01', TO_CHILD)

##        HW_object_type_str = 'TremulantWaveformPipe'
##        if HW_object_type_str in self.HW_ODF_dic.keys():
##            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
##                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PipeID', 'Pipe_SoundEngine01', TO_CHILD)
## cancelled, when used in some sample set, it points to PipeID values which none exits

        HW_object_type_str = 'Tremulant'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ControllingSwitchID', 'Switch', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PhaseAngleOutputContinuousControlID', 'ContinuousControl', TO_PARENT)

        HW_object_type_str = 'TremulantWaveform'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'TremulantID', 'Tremulant', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PhaseAngleOutputContinuousControlID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PitchOutputContinuousControlID', 'ContinuousControl', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'PitchAndFundamentalWaveformSampleID', 'Sample', TO_CHILD)

        HW_object_type_str = 'ImageSetInstance'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                if len(HW_object_dic['_parents']) == 0:
                    # this ImageSetInstance object has none parent, link it with its DisplayPage
                    self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'DisplayPageID', 'DisplayPage', TO_PARENT)
                self.HW_ODF_do_link_between_obj_by_id(HW_object_dic, 'ImageSetID', 'ImageSet', TO_CHILD)

        # link to _General all the Division objects
        HW_object_type_str = 'Division'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj(HW_object_dic, HW_general_object_dic, TO_PARENT)

        # link to _General all the DisplayPage objects
        HW_object_type_str = 'DisplayPage'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                self.HW_ODF_do_link_between_obj(HW_object_dic, HW_general_object_dic, TO_PARENT)

        # link to _General all the WindCompartment objects which have no parent
        HW_object_type_str = 'WindCompartment'
        if HW_object_type_str in self.HW_ODF_dic.keys():
            for HW_object_dic in self.HW_ODF_dic[HW_object_type_str].values():
                if len(HW_object_dic['_parents']) == 0:
                    self.HW_ODF_do_link_between_obj(HW_object_dic, HW_general_object_dic, TO_PARENT)

##        # link to _General all the objects but some object types which have no parent despite all the links created above
##        for HW_object_type_str, object_type_dic in self.HW_ODF_dic.items():
##            if not HW_object_type_str.startswith(('Pi', 'Sa', '_G', 'TremulantWaveformP')):  # exclude objects Pipe_SoundEngine01..., Sample, _General
##                for HW_object_dic in object_type_dic.values():
##                    if len(HW_object_dic['_parents']) == 0:
##                        # the current object has no parent
##                        self.HW_ODF_do_link_between_obj(HW_object_dic, HW_general_object_dic, TO_PARENT)

        return True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_do_link_between_obj_by_id(self, HW_object_dic, HW_attr_id_name_str, linked_object_type_str, link_type_int):
        # do a link between the given HW object dict and the given linked HW object type dict based on an ID
        # the given link_type_int must be TO_PARENT or TO_CHILD

        # recover the value of the ID permitting to establish a linkage between the two objects
        linkage_id_value_int = myint(self.HW_ODF_get_attribute_value(HW_object_dic, HW_attr_id_name_str))

        if linkage_id_value_int != None:
            try:
                linked_object_dic = self.HW_ODF_dic[linked_object_type_str][linkage_id_value_int]
            except:
                self.events_log_add(f'INTERNAL ERROR : object type {linked_object_type_str} with ID {linkage_id_value_int} not found')
                return False
            else:
                return self.HW_ODF_do_link_between_obj(HW_object_dic, linked_object_dic, link_type_int)
        else:
            return False

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_do_link_between_obj(self, HW_object_dic, linked_HW_object_dic, link_type_int):
        # do a link between the given HW object dict and the given linked HW object dict
        # the given link_type_int must be TO_PARENT or TO_CHILD

        if link_type_int == TO_CHILD:
            self.HW_ODF_add_attribute_value(HW_object_dic, '_children', linked_HW_object_dic)
            self.HW_ODF_add_attribute_value(linked_HW_object_dic, '_parents', HW_object_dic)
        elif link_type_int == TO_PARENT:
            self.HW_ODF_add_attribute_value(HW_object_dic, '_parents', linked_HW_object_dic)
            self.HW_ODF_add_attribute_value(linked_HW_object_dic, '_children', HW_object_dic)
        else:
            self.events_log_add('INTERNAL ERROR : undefined link type given to HW_ODF_do_link_between_obj')
            return False

        return True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_add_attribute_value(self, HW_object_dic, attr_name_str, attr_value):
        # add the given attribute value to the list of the given object dictionary of the Hauptwerk ODF dictionary (for _xxx attributes which contain a list)
        # if the given value already exists in the list, it is not added to avoid doubles
        # return True or False whether the operation has succeeded or not

        try:
            if attr_value not in HW_object_dic[attr_name_str]:
                HW_object_dic[attr_name_str].append(attr_value)
        except:
            # the attr_name_str doesn't exist, create it and add the value
            HW_object_dic[attr_name_str] = []
            HW_object_dic[attr_name_str].append(attr_value)

        return True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_attribute_value(self, HW_object_dic, attr_name_str, mandatory_bool=False):
        # return the string value string of the given attribute defined in the given object sub-dictionary of the Hauptwerk ODF dictionary
        # generate a log in case of attribute not found and if mandatory_bool=True, mandatory_bool=False permits to get silently an attribute which the presence is optional
        # return None if the attribute name is not defined in the given dictionary

        if HW_object_dic == None:
            return None

        try:
            attr_value = HW_object_dic[attr_name_str]
        except:
            attr_value = None
            if mandatory_bool:
                self.events_log_add(f'ERROR : unable to read the attribute "{attr_name_str}" in the sample set object {HW_object_dic["_HW_uid"]}')

        return attr_value

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_object_dic(self, HW_object_type_or_uid_str, HW_object_id_int = None):
        # return the HW object dictionary having the given object type and ID or only the given UID (unique ID) if object_id_int = -1 or not defined
        # if the HW object type is '_General' then the object ID parameter has not to be provided
        # return None if the object has not been found with the given data

        # define the object type and ID
        if HW_object_id_int == None:
            # no object ID provided : object UID is provided
            if HW_object_type_or_uid_str == '_General':
                HW_object_type_str = '_General'
                HW_object_id_int = 1
            else:
                HW_object_type_str = HW_object_type_or_uid_str[:-6]    # remove the last 6 digits of the UID
                HW_object_id_int = myint(HW_object_type_or_uid_str[-6:])  # keep only the last 6 digits of the UID
        else:
            # object type + ID is provided
            HW_object_type_str = HW_object_type_or_uid_str

        if HW_object_id_int == 0:
            return None

        try:
            # recover the dictionary of the object having the given type and ID
            return self.HW_ODF_dic[HW_object_type_str][HW_object_id_int]
        except:
            # object dictionary not existing for the given type and/or ID
            return None

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_object_dic_by_ref_id(self, HW_object_type_str, ref_HW_object_dic, ref_HW_attr_id_name_str):
        # return the HW object dictionary having the given object type and which the ID is defined in the given referencing object dictionary and its referencing attribute ID

        # get the ID of the referenced object
        HW_object_id_int = myint(self.HW_ODF_get_attribute_value(ref_HW_object_dic, ref_HW_attr_id_name_str))

        if HW_object_id_int != None:
            return self.HW_ODF_get_object_dic(HW_object_type_str, HW_object_id_int)
        else:
            return None

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_linked_objects_dic_by_type(self, HW_object_dic, object_type_str, link_type_int, only_first_one_bool=False):
        # return a list containing the dictionary of the objects which are parent/child of the given object and which has the given object type
        # the given link_type_int must be TO_PARENT or TO_CHILD
        # if only_first_one_bool = True, only the first occurence is returned as a dictionary, not as a list
        # return an empty list or None (if only first one) if there is no parent/child found

        HW_linked_objects_dic_list = []
        HW_linked_object_dic = None

        if HW_object_dic != None:
            if link_type_int == TO_PARENT:
                for HW_obj_dic in HW_object_dic['_parents']:
                    if HW_obj_dic['_HW_uid'][:-6] == object_type_str:
                        if only_first_one_bool:
                            HW_linked_object_dic = HW_obj_dic
                            break
                        else:
                            HW_linked_objects_dic_list.append(HW_obj_dic)

            elif link_type_int == TO_CHILD:
                for HW_obj_dic in HW_object_dic['_children']:
                    if HW_obj_dic['_HW_uid'][:-6] == object_type_str:
                        if only_first_one_bool:
                            HW_linked_object_dic = HW_obj_dic
                            break
                        else:
                            HW_linked_objects_dic_list.append(HW_obj_dic)
            else:
                self.events_log_add('INTERNAL ERROR : undefined link type given to HW_ODF_get_linked_objects_dic_by_type')

        if only_first_one_bool:
            return HW_linked_object_dic
        else:
            return HW_linked_objects_dic_list

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_object_data_list(self, HW_object_uid_str):
        # return a list containing the object attributes name/value of the given object UID (for display purpose in the GUI)

        HW_object_dic = self.HW_ODF_get_object_dic(HW_object_uid_str)
        data_list = []

        if HW_object_dic != None:
            for obj_attr_name_str, obj_attr_value in HW_object_dic.items():
                if obj_attr_name_str in ('_parents', '_children'):
                    # this attribute contains a list of objects dictionaries
                    obj_attr_value_str = ''
                    for HW_object_dic2 in obj_attr_value:
                        obj_attr_value_str += HW_object_dic2['_HW_uid'] + '  '
                else:
                    obj_attr_value_str = str(obj_attr_value)
                data_list.append(f'{obj_attr_name_str}={obj_attr_value_str}')

        return data_list

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_image_attributes(self, HW_object_dic, HW_image_attr_dic, HW_image_index_in_set_int = None):
        # fill the given image dictionary with the following HW attributes of the given object dictionary (can be ImageSetInstance or ImageSet) and the related ImageSet / ImageSetElement
        # the not defined attributes are set at None
        #    Name (string)
        #    LeftXPosPixels (integer)
        #    TopYPosPixels (integer)
        #    ImageWidthPixels (integer)
        #    ImageHeightPixels (integer)
        #    ImageWidthPixelsTiling (integer)
        #    ImageHeightPixelsTiling (integer)
        #    ClickableAreaLeftRelativeXPosPixels (integer)
        #    ClickableAreaRightRelativeXPosPixels (integer)
        #    ClickableAreaTopRelativeYPosPixels (integer)
        #    ClickableAreaBottomRelativeYPosPixels (integer)
        #    InstallationPackageID (integer)
        #    BitmapFilename (string)
        #    TransparencyMaskBitmapFilename (string)
        # in case of an ImageSetInstance as object type, use the object default image index in set to know which ImageSetElement to recover
        # in case of an ImageSet as object type, use the given image index in set to know which ImageSetElement to recover
        # return True or False whether the operation has succeeded or not

        if HW_object_dic['_HW_uid'][:-6] == 'ImageSetInstance':
            # ImageSetInstance object provided

            HW_image_set_inst_dic = HW_object_dic

            # recover the dictionary of the associated ImageSet object
            HW_image_set_dic = self.HW_ODF_get_object_dic_by_ref_id('ImageSet', HW_image_set_inst_dic, 'ImageSetID')
            if HW_image_set_dic == None: return False

            HW_image_attr_dic['Name'] = self.HW_ODF_get_attribute_value(HW_image_set_inst_dic, 'Name')

            HW_image_attr_dic['LeftXPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_inst_dic, 'LeftXPosPixels'))
            HW_image_attr_dic['TopYPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_inst_dic, 'TopYPosPixels'))

            HW_image_attr_dic['ImageWidthPixelsTiling'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_inst_dic, 'RightXPosPixelsIfTiling'))
            if HW_image_attr_dic['ImageWidthPixelsTiling'] == 0: HW_image_attr_dic['ImageWidthPixelsTiling'] = None

            HW_image_attr_dic['ImageHeightPixelsTiling'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_inst_dic, 'BottomYPosPixelsIfTiling'))
            if HW_image_attr_dic['ImageHeightPixelsTiling'] == 0: HW_image_attr_dic['ImageHeightPixelsTiling'] = None

            if HW_image_index_in_set_int == None:
                # image index not provided in parameter of the function : set a default index
                HW_image_index_in_set_int = myint(self.HW_ODF_get_attribute_value(HW_image_set_inst_dic, 'DefaultImageIndexWithinSet'))
                # if the attribute ImageIndexWithinSet is not defined, set the index at 1 by default
                if HW_image_index_in_set_int == None: HW_image_index_in_set_int = 1

        elif HW_object_dic['_HW_uid'][:-6] == 'ImageSet':
            # ImageSet object provided
            HW_image_set_inst_dic = None
            HW_image_set_dic = HW_object_dic

            HW_image_attr_dic['Name'] = self.HW_ODF_get_attribute_value(HW_image_set_dic, 'Name')
            HW_image_attr_dic['LeftXPosPixels'] = None
            HW_image_attr_dic['TopYPosPixels'] = None
            HW_image_attr_dic['ImageWidthPixelsTiling'] = None
            HW_image_attr_dic['ImageHeightPixelsTiling'] = None

        else:
            return False

        # recover the data from the ImageSet
        HW_image_attr_dic['InstallationPackageID'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'InstallationPackageID', True))

        if HW_image_attr_dic['ImageWidthPixelsTiling'] != None:
            HW_image_attr_dic['ImageWidthPixels'] = HW_image_attr_dic['ImageWidthPixelsTiling']
        else:
            HW_image_attr_dic['ImageWidthPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'ImageWidthPixels'))

        if HW_image_attr_dic['ImageHeightPixelsTiling'] != None:
            HW_image_attr_dic['ImageHeightPixels'] = HW_image_attr_dic['ImageHeightPixelsTiling']
        else:
            HW_image_attr_dic['ImageHeightPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'ImageHeightPixels'))

        # recover the bitmap file of the transparency image
        ret = self.HW_ODF_get_attribute_value(HW_image_set_dic, 'TransparencyMaskBitmapFilename')
        if ret != None:
            HW_image_attr_dic['TransparencyMaskBitmapFilename'] = self.convert_file_name(ret, HW_image_attr_dic['InstallationPackageID'])
        else:
            HW_image_attr_dic['TransparencyMaskBitmapFilename'] = None

        # recover the bitmap file of the displayed image (from the ImageSetElement associated to the ImageSet and having the proper image index within set)
        HW_image_attr_dic['BitmapFilename'] = None
        for image_set_elem_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_image_set_dic, 'ImageSetElement', TO_CHILD):
            # parse the ImageSetElement objects which are children of the ImageSet object to find the one having the right image index
            image_index = myint(self.HW_ODF_get_attribute_value(image_set_elem_dic, 'ImageIndexWithinSet'))
            if image_index == None: image_index = 1  # if the attribute ImageIndexWithinSet is not defined, it is the index 1 by default
            if image_index == HW_image_index_in_set_int:
                # it is the expected ImageSetElement object
                ret = self.HW_ODF_get_attribute_value(image_set_elem_dic, 'BitmapFilename', True)
                if ret != None:
                    HW_image_attr_dic['BitmapFilename'] = self.convert_file_name(ret, HW_image_attr_dic['InstallationPackageID'])
                else:
                    HW_image_attr_dic['BitmapFilename'] = None
                break

        HW_image_attr_dic['ClickableAreaLeftRelativeXPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'ClickableAreaLeftRelativeXPosPixels'))
        HW_image_attr_dic['ClickableAreaRightRelativeXPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'ClickableAreaRightRelativeXPosPixels'))
        HW_image_attr_dic['ClickableAreaTopRelativeYPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'ClickableAreaTopRelativeYPosPixels'))
        HW_image_attr_dic['ClickableAreaBottomRelativeYPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_image_set_dic, 'ClickableAreaBottomRelativeYPosPixels'))

        # correct the clickable width if greater than the image width
        if (HW_image_attr_dic['ImageWidthPixels'] != None and HW_image_attr_dic['ClickableAreaRightRelativeXPosPixels'] != None and
            HW_image_attr_dic['ClickableAreaRightRelativeXPosPixels'] > HW_image_attr_dic['ImageWidthPixels'] - 1):
            HW_image_attr_dic['ClickableAreaRightRelativeXPosPixels'] = HW_image_attr_dic['ImageWidthPixels'] - 1
        # correct the clickable height if greater than the image height
        if (HW_image_attr_dic['ImageHeightPixels'] != None and HW_image_attr_dic['ClickableAreaBottomRelativeYPosPixels'] != None and
            HW_image_attr_dic['ClickableAreaBottomRelativeYPosPixels'] > HW_image_attr_dic['ImageHeightPixels'] - 1):
            HW_image_attr_dic['ClickableAreaBottomRelativeYPosPixels'] = HW_image_attr_dic['ImageHeightPixels'] - 1

        # set some default values if not defined
        if HW_image_attr_dic['LeftXPosPixels'] == None: HW_image_attr_dic['LeftXPosPixels'] = 0
        if HW_image_attr_dic['TopYPosPixels'] == None: HW_image_attr_dic['TopYPosPixels'] = 0

        return True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_text_attributes(self, HW_text_inst_dic, HW_text_attr_dic):
        # fill the given HW_text_attr_dic dictionary with the following HW attributes of the given TextInstance object dictionary (+ ImageSetInstance if any) and the related TextStyle
        # the not defined attributes are set at None
        #    Text (string)
        #    XPosPixels (integer)
        #    YPosPixels (integer)
        #    AttachedToAnImageSetInstance : Y or N (string)
        #    PosRelativeToTopLeftOfImage : Y or N (string)
        #    BoundingBoxWidthPixelsIfWordWrap (integer)
        #    BoundingBoxHeightPixelsIfWordWrap (integer)
        #    Face_WindowsName (string)
        #    Font_SizePixels (integer)
        #    Font_WeightCode : 1 = light, 2 = normal, 3 = bold (integer)
        #    Colour_Red (integer)
        #    Colour_Green (integer)
        #    Colour_Blue (integer)
        #    HorizontalAlignmentCode : 0 = center, 1 = left, 2 = right (integer)
        #    VerticalAlignmentCode   : 0 = center, 1 or not defined = top, 2 = bottom (integer)
        #    + the attributes returned by HW_ODF_get_image_attributes if an image is attached to this TextInstance object
        #    ImageSetInstanceDic : dictionary of the linked ImageSetInstance if any, else None

        if not HW_text_inst_dic['_HW_uid'][:-6] == 'TextInstance':
            return False

        HW_text_attr_dic['Text'] = self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'Text', True)
        HW_text_attr_dic['XPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'XPosPixels'))
        HW_text_attr_dic['YPosPixels'] = myint(self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'YPosPixels'))
        HW_text_attr_dic['AttachedToAnImageSetInstance'] = self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'AttachedToAnImageSetInstance')
        HW_text_attr_dic['PosRelativeToTopLeftOfImage'] = self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'PosRelativeToTopLeftOfImageSetInstance')
        HW_text_attr_dic['BoundingBoxWidthPixelsIfWordWrap'] = myint(self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'BoundingBoxWidthPixelsIfWordWrap'))
        HW_text_attr_dic['BoundingBoxHeightPixelsIfWordWrap'] = myint(self.HW_ODF_get_attribute_value(HW_text_inst_dic, 'BoundingBoxHeightPixelsIfWordWrap'))

        # recover the data from the associated TextStyle object
        HW_text_style_dic = self.HW_ODF_get_object_dic_by_ref_id('TextStyle', HW_text_inst_dic, 'TextStyleID')
        if HW_text_style_dic != None:
            HW_text_attr_dic['Face_WindowsName'] = self.HW_ODF_get_attribute_value(HW_text_style_dic, 'Face_WindowsName')
            HW_text_attr_dic['Font_SizePixels'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'Font_SizePixels'))

            HW_text_attr_dic['Font_WeightCode'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'Font_WeightCode'))

            HW_text_attr_dic['Colour_Red'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'Colour_Red'))
            HW_text_attr_dic['Colour_Green'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'Colour_Green'))
            HW_text_attr_dic['Colour_Blue'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'Colour_Blue'))

            HW_text_attr_dic['HorizontalAlignmentCode'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'HorizontalAlignmentCode'))
            HW_text_attr_dic['VerticalAlignmentCode'] = myint(self.HW_ODF_get_attribute_value(HW_text_style_dic, 'VerticalAlignmentCode'))
        else:
            HW_text_attr_dic['Face_WindowsName'] = None
            HW_text_attr_dic['Font_SizePixels'] = None
            HW_text_attr_dic['Font_WeightCode'] = None
            HW_text_attr_dic['Colour_Red'] = None
            HW_text_attr_dic['Colour_Green'] = None
            HW_text_attr_dic['Colour_Blue'] = None
            HW_text_attr_dic['HorizontalAlignmentCode'] = None
            HW_text_attr_dic['VerticalAlignmentCode'] = None

        # set some default values if not defined
        if HW_text_attr_dic['Face_WindowsName'] == None: HW_text_attr_dic['Face_WindowsName'] = 'Arial'
        if HW_text_attr_dic['Font_SizePixels'] == None: HW_text_attr_dic['Font_SizePixels'] = 10
        if HW_text_attr_dic['Font_WeightCode'] == None: HW_text_attr_dic['Font_WeightCode'] = 2
        if HW_text_attr_dic['HorizontalAlignmentCode'] == None: HW_text_attr_dic['HorizontalAlignmentCode'] = 0
        if HW_text_attr_dic['VerticalAlignmentCode'] == None: HW_text_attr_dic['VerticalAlignmentCode'] = 1
        if HW_text_attr_dic['XPosPixels'] == None: HW_text_attr_dic['XPosPixels'] = 0
        if HW_text_attr_dic['YPosPixels'] == None: HW_text_attr_dic['YPosPixels'] = 0

        # add in the HW_text_attr_dic the attributes of the associated ImageSetInstance object if one is defined
        HW_image_set_inst_dic = self.HW_ODF_get_object_dic_by_ref_id('ImageSetInstance', HW_text_inst_dic, 'AttachedToImageSetInstanceID')
        HW_text_attr_dic['ImageSetInstanceDic'] = HW_image_set_inst_dic
        if HW_image_set_inst_dic != None:
            self.HW_ODF_get_image_attributes(HW_image_set_inst_dic, HW_text_attr_dic)

        return True

    #-------------------------------------------------------------------------------------------------
##    def HW_ODF_get_switch_controllers(self, switch_dic, switches_dic_list, cond_switches_dic_list):
##        # recursive fonction to fill the given switches_dic_list list with the clickable Switch objects having a control on the given Switch object
##        # recursive fonction to fill the given switches_dic_list list with the displayed Switch objects having a control on the given Switch object

##        if switch_dic['_disp_page_id'] != '':
##            # the given Switch object is visible in a display page : add it to the switches lists
##        if self.HW_ODF_get_attribute_value(switch_dic, 'Clickable') == 'Y':
##            # the given Switch object is clickable : add it to the switches lists
##            switches_dic_list.append(switch_dic)
##
##         for src_switch_uid in switch_dic['_src']:
##            # parse the source switches list and add their controller switch in the switches_dic_list
##            src_switch_dic = self.HW_ODF_get_object_dic(src_switch_uid)
##            if src_switch_dic not in switches_dic_list:
##                # the switch is not already mentioned in the list
##                self.HW_ODF_get_switch_controllers(src_switch_dic, switches_dic_list, cond_switches_dic_list)

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_get_controlled_switches(self, HW_switch_dic, HW_ctrl_object_type_str, HW_switch_data_dic):
        # recursive fonction to make the list of the HW Switch objects having the given object type name which are controlled by the given HW Switch
        # return in the given HW_switch_data_dic :
        #     controlled_switches : list of the controlled HW switches
        #     switch_asgn_code : value of the attribute DefaultInputOutputSwitchAsgnCode if found in one of the controlled switches

        if len(HW_switch_data_dic) == 0:
            # dictionary empty, create the two keys
            HW_switch_data_dic['controlling_switches'] = []  # list of all HW Switch objects having control on the HW object type starting from the given HW Switch
            HW_switch_data_dic['controlled_switches'] = [] # list of HW Switch objects controlling directly (is parent of) a HW object of the given object type
            HW_switch_data_dic['switch_asgn_code'] = None
##            HW_switch_data_dic['conditional'] = False

        if HW_switch_dic not in HW_switch_data_dic['controlling_switches']:
            # the given HW switch has not been already checked in a previous recursive call
            asgn_code = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'DefaultInputOutputSwitchAsgnCode'))
            if asgn_code != None:
                HW_switch_data_dic['switch_asgn_code'] = asgn_code

            if self.HW_ODF_get_linked_objects_dic_by_type(HW_switch_dic, HW_ctrl_object_type_str, TO_CHILD, True) != None:
                # the given HW Switch controls (is parent of) a HW object of the given object type name
                HW_switch_data_dic['controlled_switches'].append(HW_switch_dic)

            HW_switch_data_dic['controlling_switches'].append(HW_switch_dic)

            for HW_child_switch_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_switch_dic, 'Switch', TO_CHILD):
                # parse the children switches which are controlled by the given HW Switch
                self.HW_ODF_get_controlled_switches(HW_child_switch_dic, HW_ctrl_object_type_str, HW_switch_data_dic)

##            for HW_child_link_switch_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_switch_dic, 'SwitchLinkage', TO_CHILD):
##                # parse the children SwitchLinkage of the given HW Switch
##                HW_dest_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_child_link_switch_dic, 'DestSwitchID')
##                HW_cond_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_child_link_switch_dic, 'ConditionSwitchID')
##                ret = self.HW_ODF_get_controlled_switches(HW_dest_switch_dic, HW_ctrl_object_type_str, HW_switch_data_dic)
##                if ret == True and HW_switch_dic == HW_cond_switch_dic:
##                    HW_switch_data_dic['conditional'] = True

    #-------------------------------------------------------------------------------------------------
    def HW_ODF_save2organfile(self, file_name_str):
        # save the Hauptwerk ODF objects dictionary into the given .organ ODF file in a GrandOrgue like format (for development/debug purpose)

        with open(file_name_str, 'w', encoding=ENCODING_UTF8_BOM) as f:
            f.write(';Hauptwerk ODF XML formatted in a GrandOrgue ODF manner\n')
            f.write('\n')
            for object_type_dic in self.HW_ODF_dic.values():
                for HW_object_dic in object_type_dic.values():
                    f.write(f'[{HW_object_dic["_HW_uid"]}]\n')
                    for obj_attr_name_str, obj_attr_value in HW_object_dic.items():
                        if obj_attr_name_str in ('_parents', '_children'):
                            # this attribute contains a list of objects dictionaries
                            obj_attr_value_str = ''
                            for HW_object_dic2 in obj_attr_value:
                                obj_attr_value_str += HW_object_dic2['_HW_uid'] + '  '
                        else:
                            obj_attr_value_str = str(obj_attr_value)
                        f.write(f'{obj_attr_name_str}={obj_attr_value_str}\n')
                    f.write('\n')

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_save2organfile(self, file_name_str):
        # save the GrandOrgue ODF objects dictionary into the given .organ ODF file
        # return True or False whether the saving has succeeded or not

        # check the extension of the given file name
        filename_str, file_extension_str = os.path.splitext(file_name_str)
        if file_extension_str != '.organ':
            self.events_log_add(f'The file "{file_name_str}" does not have the expected extension .organ')
            return False

        with open(file_name_str, 'w', encoding=ENCODING_UTF8_BOM) as f:
            f.write(';GrandOrgue ODF automatically generated from a Hauptwerk ODF by the OdfEdit tool (github.com/GrandOrgue/ODFEdit)\n')
            f.write('\n')
            for obj_id, obj_attr_dic in self.GO_ODF_dic.items():
                f.write(f'[{obj_id}]\n')
                for obj_attr_name_str, obj_attr_value_str in obj_attr_dic.items():
                    f.write(f'{obj_attr_name_str}={obj_attr_value_str}\n')
                f.write('\n')

        self.events_log_add(f'GrandOrgue ODF built and saved in "{file_name_str}"')
        self.events_log_add(f'It can be loaded in GrandOrgue')
        return True

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_from_HW_ODF(self, HW_ODF_file_name_str, GO_ODF_file_name, progress_status_update_fct):
        # build and save a GrandOrgue ODF from the given Hauptwerk ODF and its associated sample set (which is not touched)
        # use the given function callback to display a progression status in the GUI
        # return False if an issue has occured, else return True

        # load the HW ODF in the HW ODF dictionary
        progress_status_update_fct('Loading the Hauptwerk ODF...')
        if self.HW_ODF_load_from_file(HW_ODF_file_name_str):

            # link the HW objects together
            progress_status_update_fct('Building the Hauptwerk ODF objects tree...')
            self.HW_ODF_do_links_between_objects()

            # clear the content of the GO ODF dictionary
            self.GO_ODF_dic.clear()

            # reset the content of the GO object types numbers dictionary
            self.GO_objects_type_nb_dic.clear()
            self.GO_objects_type_nb_dic['Stop'] = 0
            self.GO_objects_type_nb_dic['Coupler'] = 0

            # build the various GO objects in the GO ODF dictionary from the HW ODF
            # the order of calling the below functions is important, there are dependencies between some of them

            progress_status_update_fct('Building the GrandOrgue Organ object...')
            if self.GO_ODF_build_Organ_object() == None :
                self.events_log_add(f'ERROR : issue occured while building the GO Organ object')
                return False

            progress_status_update_fct('Building the GrandOrgue WindchestGroup objects...')
            if self.GO_ODF_build_WindchestGroup_objects() == 0 :
                self.events_log_add(f'ERROR : no GO WindchestGroup object could be created')
                return False

            progress_status_update_fct('Building the GrandOrgue Rank objects...')
            if self.GO_ODF_build_Rank_objects() == 0 :
                self.events_log_add(f'ERROR : no GO Rank object could be created')
                return False

            # build the GO Panel objects by sorted HW DisplayPage ID
            progress_status_update_fct('Building the GrandOrgue Panel objects...')
            for HW_disp_page_id in sorted(self.HW_ODF_dic['DisplayPage'].keys()):
                HW_disp_page_dic = self.HW_ODF_get_object_dic('DisplayPage', HW_disp_page_id)
                self.GO_ODF_build_Panel_object(HW_disp_page_dic)

            # build the GO Manual objects by HW DisplayPage
            progress_status_update_fct('Building the GrandOrgue Manual objects...')
            for HW_disp_page_dic in self.HW_ODF_dic['DisplayPage'].values():
                for HW_keyboard_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_page_dic, 'Keyboard', TO_CHILD):
                    # parse the HW Keyboard objects of the current display page
                    self.GO_ODF_build_Manual_object(HW_keyboard_dic)
                for HW_disp_switch_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_page_dic, 'Switch', TO_CHILD):
                    # parse the HW Switch objects of the current HW DisplayPage
                    HW_keyboard_key_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_switch_dic, 'KeyboardKey', TO_CHILD, True)
                    if HW_keyboard_key_dic != None:
                        # the current HW Switch is linked to a KeyboardKey object
                        if HW_keyboard_key_dic['_GO_uid'] == '':
                            # the HW KeyboardKey not already assigned to a GO object
                            self.GO_ODF_build_Manual_object(HW_keyboard_key_dic)

            # build the other GO objects by sorted HW DisplayPage ID
            progress_status_update_fct('Building the GrandOrgue control objects...')
            for HW_disp_page_id in sorted(self.HW_ODF_dic['DisplayPage'].keys()):
                HW_disp_page_dic = self.HW_ODF_get_object_dic('DisplayPage', HW_disp_page_id)
                for HW_disp_switch_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_page_dic, 'Switch', TO_CHILD):
                    # parse the HW Switch objects displayed in the current HW DisplayPage
                    if HW_disp_switch_dic['_GO_uid'] == '':
                        # the HW Switch is not already assigned to a GO object
                        # look for controlled HW Stop objects
                        HW_switch_data_dic = {}
                        self.HW_ODF_get_controlled_switches(HW_disp_switch_dic, 'Stop', HW_switch_data_dic)
                        if len(HW_switch_data_dic['controlled_switches']) > 0:
                            # the HW Switch is controlling HW Stop object(s)
                            for HW_ctrl_switch_dic in HW_switch_data_dic['controlled_switches']:
                                self.GO_ODF_build_Stop_object(HW_ctrl_switch_dic, HW_switch_data_dic['controlling_switches'])
                        # look for controlled HW KeyAction objects
                        HW_switch_data_dic = {}
                        self.HW_ODF_get_controlled_switches(HW_disp_switch_dic, 'KeyAction', HW_switch_data_dic)
                        if len(HW_switch_data_dic['controlled_switches']) > 0:
                            # the HW Switch is controlling HW KeyAction object (only one normally)
                            for HW_ctrl_switch_dic in HW_switch_data_dic['controlled_switches']:
                                self.GO_ODF_build_Coupler_object(HW_ctrl_switch_dic, HW_switch_data_dic['controlling_switches'])


            progress_status_update_fct('Completing the build...')
##            print(self.GO_objects_type_nb_dic)

            # remove from the GO ODF the attributes _GO_uid added in Panel and Manual objects to help in building the ODF
            for obj_uid, obj_attr_dic in self.GO_ODF_dic.items():
                if obj_uid[:-3] in ('Panel', 'Manual'):
                    obj_attr_list = list(obj_attr_dic.keys())
                    for obj_attr_name_str in obj_attr_list:
                        if obj_attr_name_str == '_GO_uid':
                            del self.GO_ODF_dic[obj_uid][obj_attr_name_str]

            # save the HW ODF data in a GO ODF format (for development/debug purpose)
##            self.HW_ODF_save2organfile(HW_ODF_file_name_str + '.organ')

            # save the built GO ODF data in a .organ file
            self.GO_ODF_save2organfile(GO_ODF_file_name)

        progress_status_update_fct('')
        return True

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Organ_object(self):
        # build the GO Organ object from the HW ODF
        # return None if an issue has occured, else return the created GO Organ dictionary

        # get the dictionary of the HW _General object
        HW_general_dic = self.HW_ODF_get_object_dic('_General')
        if HW_general_dic == None:
            self.events_log_add(f'ERROR : missing _General object in the Hauptwerk ODF dictionary')
            return None

        # check if the folders of the required installation packages are present in the folder OrganInstallationPackages
        self.HW_packages_id_list = []  # list storing the ID of the installation packages which are actually accessible in the sample set package
        for HW_install_pack_dic in self.HW_ODF_dic['RequiredInstallationPackage'].values():
            # parse and check the defined HW RequiredInstallationPackage objects
            HW_package_id = myint(self.HW_ODF_get_attribute_value(HW_install_pack_dic, 'InstallationPackageID', True))
            if HW_package_id == None:
                return None

            HW_package_name = self.HW_ODF_get_attribute_value(HW_install_pack_dic, 'Name', True)
            HW_package_supplier = self.HW_ODF_get_attribute_value(HW_install_pack_dic, 'SupplierName', True)
            if HW_package_name == None or HW_package_supplier == None:
                return None

            folder_name = os.path.dirname(self.HW_ODF_file_name_str) + '/' + str(HW_package_id).zfill(6)
            folder_name = folder_name.replace('OrganDefinitions', 'OrganInstallationPackages')
            folder_name = folder_name.replace('/', '\\')
            if not os.path.isdir(folder_name):
                # the folder doesn't exist in the sample set package
                self.events_log_add(f'WARNING : The package ID {HW_package_id} named "{HW_package_name}" provided by "{HW_package_supplier}"')
                self.events_log_add(f'WARNING : is not present in the folder {folder_name}')
                self.events_log_add(f'WARNING : Some graphical or sound elements of this organ may be not rendered in GrandOrgue')
            else:
                self.HW_packages_id_list.append(HW_package_id)

        # recover the main installation package ID
        HW_install_package_id = myint(self.HW_ODF_get_attribute_value(HW_general_dic, 'OrganInfo_InstallationPackageID', True))
        if HW_install_package_id == None:
            return None

        # add an entry in the GO ODF dictionary for the Organ object
        GO_organ_dic = self.GO_ODF_dic['Organ'] = {}

        GO_organ_dic['ChurchName'] = self.HW_ODF_get_attribute_value(HW_general_dic, 'Identification_Name')
        GO_organ_dic['ChurchAddress'] = self.HW_ODF_get_attribute_value(HW_general_dic, 'OrganInfo_Location')
        GO_organ_dic['OrganBuilder'] = self.HW_ODF_get_attribute_value(HW_general_dic, 'OrganInfo_Builder')
        GO_organ_dic['OrganBuildDate'] = self.HW_ODF_get_attribute_value(HW_general_dic, 'OrganInfo_BuildDate')
        #GO_organ_dic['OrganComments'] = self.HW_ODF_get_attribute_value(HW_general_dic, 'OrganInfo_Comments')
        GO_organ_dic['OrganComments'] = 'GrandOrgue definition file automatically generated by the tool OdfEdit for a sample set made for Hauptwerks'
        GO_organ_dic['RecordingDetails'] = self.HW_ODF_get_attribute_value(HW_general_dic, 'Control_OrganDefinitionSupplierName', True)

        GO_organ_dic['InfoFilename'] = self.convert_file_name(self.HW_ODF_get_attribute_value(HW_general_dic, 'OrganInfo_InfoFilename'), HW_install_package_id)

        GO_organ_dic['HasPedals'] = 'N'
        GO_organ_dic['NumberOfManuals'] = 0
        GO_organ_dic['NumberOfPanels'] = 0
        GO_organ_dic['NumberOfWindchestGroups'] = 0
        GO_organ_dic['NumberOfRanks'] = 0
        GO_organ_dic['NumberOfSwitches'] = 0
        GO_organ_dic['NumberOfEnclosures'] = 0
        GO_organ_dic['NumberOfTremulants'] = 0
        GO_organ_dic['NumberOfGenerals'] = 0
        GO_organ_dic['NumberOfDivisionalCouplers'] = 0
        GO_organ_dic['NumberOfReversiblePistons'] = 0

        GO_organ_dic['GeneralsStoreDivisionalCouplers'] = 'Y'
        GO_organ_dic['DivisionalsStoreTremulants'] = 'Y'
        GO_organ_dic['DivisionalsStoreIntermanualCouplers'] = 'Y'
        GO_organ_dic['DivisionalsStoreIntramanualCouplers'] = 'Y'
        GO_organ_dic['CombinationsStoreNonDisplayedDrawstops'] = 'N'

        GO_organ_dic['Gain'] = str(float(self.HW_ODF_get_attribute_value(HW_general_dic, 'AudioOut_AmplitudeLevelAdjustDecibels')))

        # recover the ID of the HW default display page (will be used in other GO_ODF_build_xxx functions)
        self.HW_default_display_page_id = myint(self.HW_ODF_get_attribute_value(HW_general_dic, 'SpecialObjects_DefaultDisplayPageID', True))
        if self.HW_default_display_page_id == None:
            return None

        # add in the HW _General object the ID of the corresponding GO object
        HW_general_dic['_GO_uid'] = 'Organ'

        return GO_organ_dic

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_WindchestGroup_objects(self):
        # build the WindchestGroups999 objects of the GrandOrgue ODF dictionary from the Hauptwerk ODF dictionary
        # return the number of created GO WindchestGroup object

        for HW_wind_comp_id in sorted(self.HW_ODF_dic['WindCompartment'].keys()):
            # parse the defined HW WindCompartment objects by increasing ID order
            HW_wind_comp_dic = self.HW_ODF_dic['WindCompartment'][HW_wind_comp_id]
            if self.HW_ODF_get_linked_objects_dic_by_type(HW_wind_comp_dic, 'Pipe_SoundEngine01', TO_CHILD, True) != None:
                # the current HW WindCompartment has at least one Pipe_SoundEngine01 child object, a corresponding GO WindchestGroup can be created
                self.GO_ODF_dic['Organ']['NumberOfWindchestGroups'] += 1
                GO_windchest_uid = 'WindchestGroup' + str(self.GO_ODF_dic['Organ']['NumberOfWindchestGroups']).zfill(3)
                GO_windchest_dic = self.GO_ODF_dic[GO_windchest_uid] = {}

                GO_windchest_dic['Name'] = self.HW_ODF_get_attribute_value(HW_wind_comp_dic, 'Name', True)
                GO_windchest_dic['NumberOfEnclosures'] = 0
                GO_windchest_dic['NumberOfTremulants'] = 0

                # add in the HW WindCompartment object the ID of the corresponding GO object
                HW_wind_comp_dic['_GO_uid'] = GO_windchest_uid

        return self.GO_ODF_dic['Organ']['NumberOfWindchestGroups']

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Rank_objects(self):
        # build the Rank999 objects of the GrandOrgue ODF dictionary from the Hauptwerk ODF dictionary
        # build as many GO Rank999 objects as HW Rank objects which have pipes defined inside
        # return the number of created GO Rank objects

        for HW_rank_id in sorted(self.HW_ODF_dic['Rank'].keys()):
            # parse the defined HW Rank objects by increasing ID order
            HW_rank_dic = self.HW_ODF_dic['Rank'][HW_rank_id]
            # get the list of the HW Pipe_SoundEngine01 objects which are children of the current HW Rank object
            HW_pipes_dic_list = self.HW_ODF_get_linked_objects_dic_by_type(HW_rank_dic, 'Pipe_SoundEngine01', TO_CHILD)
            if len(HW_pipes_dic_list) > 0:
                # the current HW rank has pipes defined inside

                # create a GO Rank999 object
                self.GO_ODF_dic['Organ']['NumberOfRanks'] += 1
                GO_rank_uid = 'Rank' + str(self.GO_ODF_dic['Organ']['NumberOfRanks']).zfill(3)
                GO_rank_dic = self.GO_ODF_dic[GO_rank_uid] = {}

                GO_rank_dic['Name'] = self.HW_ODF_get_attribute_value(HW_rank_dic, 'Name', True)

                first_midi_note_nb = 999
                last_midi_note_nb = 0
                pipes_dic = {}  # dictionnary with as key the MIDI note number and as value the dictionary of the associated Pipe_SoundEngine01 object

                for HW_pipe_dic in HW_pipes_dic_list:
                    # parse the Pipe_SoundEngine01 objects to get their MIDI note number and update the min / max note number
                    # and associate the MIDI note numbers to Pipe_SoundEngine01 objects

                    # get the MIDI note number of the current HW Pipe_SoundEngine01 object
                    midi_note_nb = myint(self.HW_ODF_get_attribute_value(HW_pipe_dic, 'NormalMIDINoteNumber'))
                    if midi_note_nb == None: midi_note_nb = 60 # observed with Sound Paradisi sample sets, the MIDI note 60 is not defined
                    if midi_note_nb < first_midi_note_nb:
                        first_midi_note_nb = midi_note_nb
                    if midi_note_nb > last_midi_note_nb:
                        last_midi_note_nb = midi_note_nb

                    # store the dictionary of the pipe associated with the MIDI note number
                    pipes_dic[midi_note_nb] = HW_pipe_dic

                GO_rank_dic['NumberOfLogicalPipes'] = len(pipes_dic)
                GO_rank_dic['FirstMidiNoteNumber'] = first_midi_note_nb
                GO_rank_dic['Percussive'] = 'N'
                GO_rank_dic['AcceptsRetuning'] = 'N'

                # use the HW source WindCompartment object of the first pipe as GO WindchestGroup of the whole GO Rank
                HW_wind_comp_dic = self.HW_ODF_get_object_dic_by_ref_id('WindCompartment', HW_pipes_dic_list[0], 'WindSupply_SourceWindCompartmentID')
                GO_windchest_uid = HW_wind_comp_dic['_GO_uid']
                GO_rank_dic['WindchestGroup'] = GO_windchest_uid[-3:]

                nb_pipes = 0
                for midi_note_nb in range(first_midi_note_nb, last_midi_note_nb + 1):
                    # parse the HW Pipe_SoundEngine01_Layer objects by increasing MIDI note number

                    if midi_note_nb in pipes_dic.keys():
                        HW_pipe_dic = pipes_dic[midi_note_nb]

                        # get the dictionary of the first Pipe_SoundEngine01_Layer child object of the current Pipe_SoundEngine01_Layer object
                        # the other Pipe_SoundEngine01_Layer objects if any exist are ignored because no possibility to manage them in GO ODF
                        HW_pipe_layer_dic_list = self.HW_ODF_get_linked_objects_dic_by_type(HW_pipe_dic, 'Pipe_SoundEngine01_Layer', TO_CHILD)
                        HW_pipe_layer_dic = HW_pipe_layer_dic_list[0]

                        # set the GO pipe ID
                        nb_pipes += 1
                        GO_pipe_uid = 'Pipe' + str(nb_pipes).zfill(3)

                        # get the pipe gain if any
                        pipe_gain = myfloat(self.HW_ODF_get_attribute_value(HW_pipe_layer_dic, 'AmpLvl_LevelAdjustDecibels'))
                        if pipe_gain != None and pipe_gain != 0:
                            GO_rank_dic[GO_pipe_uid + 'Gain'] = pipe_gain

                        # get the pipe harmonic number if any
                        pipe_harmonic_nb = myint(self.HW_ODF_get_attribute_value(HW_pipe_dic, 'Pitch_Tempered_RankBasePitch64ftHarmonicNum'))
                        if pipe_harmonic_nb != None and pipe_harmonic_nb != 0:
                            GO_rank_dic[GO_pipe_uid + 'HarmonicNumber'] = pipe_harmonic_nb

                        GO_rank_dic[GO_pipe_uid + 'LoadRelease'] = 'N'

                        # manage the attack sample
                        # get the dictionary of the first Pipe_SoundEngine01_AttackSample child object of the current Pipe_SoundEngine01_Layer object (the other are ignored)
                        HW_pipe_attack_sample_dic_list = self.HW_ODF_get_linked_objects_dic_by_type(HW_pipe_layer_dic, 'Pipe_SoundEngine01_AttackSample', TO_CHILD)
                        HW_pipe_attack_sample_dic = HW_pipe_attack_sample_dic_list[0]
                        # get the dictionary of the Sample child object of the current Pipe_SoundEngine01_AttackSample object
                        HW_sample_dic_list = self.HW_ODF_get_linked_objects_dic_by_type(HW_pipe_attack_sample_dic, 'Sample', TO_CHILD)
                        HW_sample_dic = HW_sample_dic_list[0]

                        HW_install_package_id = myint(self.HW_ODF_get_attribute_value(HW_sample_dic, 'InstallationPackageID', True))
                        GO_rank_dic[GO_pipe_uid] = self.convert_file_name(self.HW_ODF_get_attribute_value(HW_sample_dic, 'SampleFilename', True), HW_install_package_id)

                        # manage the release samples
                        # get the dictionaries list of the Pipe_SoundEngine01_ReleaseSample child objects of the current Pipe_SoundEngine01_Layer object
                        HW_pipe_release_sample_dic_list = self.HW_ODF_get_linked_objects_dic_by_type(HW_pipe_layer_dic, 'Pipe_SoundEngine01_ReleaseSample', TO_CHILD)
                        if len(HW_pipe_release_sample_dic_list) > 0:
                            # there are release samples
                            GO_rank_dic[GO_pipe_uid + 'ReleaseCount'] = len(HW_pipe_release_sample_dic_list)
                            release_count = 0
                            for HW_pipe_release_sample_dic in HW_pipe_release_sample_dic_list:

                                # get the max key release time for the current release sample
                                HW_max_key_release_time_int = myint(self.HW_ODF_get_attribute_value(HW_pipe_release_sample_dic, 'ReleaseSelCriteria_LatestKeyReleaseTimeMs'))

                                # get the dictionary of the Sample child object of the current Pipe_SoundEngine01_ReleaseSample object
                                HW_sample_dic_list = self.HW_ODF_get_linked_objects_dic_by_type(HW_pipe_release_sample_dic, 'Sample', TO_CHILD)
                                HW_sample_dic = HW_sample_dic_list[0]
                                release_count += 1

                                HW_install_package_id = myint(self.HW_ODF_get_attribute_value(HW_sample_dic, 'InstallationPackageID', True))
                                GO_rank_dic[GO_pipe_uid + 'Release' + str(release_count).zfill(3)] = self.convert_file_name(self.HW_ODF_get_attribute_value(HW_sample_dic, 'SampleFilename', True), HW_install_package_id)

                                if HW_max_key_release_time_int == None or HW_max_key_release_time_int == 99999 or HW_max_key_release_time_int == -1:
                                    GO_rank_dic[GO_pipe_uid + 'Release' + str(release_count).zfill(3) + 'MaxKeyPressTime'] = '-1'
                                else:
                                    GO_rank_dic[GO_pipe_uid + 'Release' + str(release_count).zfill(3) + 'MaxKeyPressTime'] = HW_max_key_release_time_int

                # add in the HW Rank object the ID of the corresponding GO object
                HW_rank_dic['_GO_uid'] = GO_rank_uid

        return self.GO_ODF_dic['Organ']['NumberOfRanks']

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Panel_object(self, HW_disp_page_dic):
        # build the GO Panel999 corresponding to the given HW DisplayPage
        # build also the GO Panel999Image999 and Panel999Element999 Label objects of this panel
        # return the dictionary of the created GO Panel object, or None if no panel created

        # get the ID of the HW DisplayPage object
        HW_page_id = myint(self.HW_ODF_get_attribute_value(HW_disp_page_dic, 'PageID', True))

        if self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_page_dic, 'Keyboard', TO_CHILD, True) != None:
            # the current HW DisplayPage object contains at least one Keyboard object in his children, so it is the HW console page
            self.HW_console_display_page_id = HW_page_id

        if HW_page_id == self.HW_default_display_page_id:
            # this is the HW default display page, so assigned to the GO Panel000
            GO_panel_uid = 'Panel000'
        else:
            self.GO_ODF_dic['Organ']['NumberOfPanels'] += 1  # Panel000 is not counted
            GO_panel_uid = 'Panel' + str(self.GO_ODF_dic['Organ']['NumberOfPanels']).zfill(3)
        # add an GO Panel 999 in the GO ODF dictionary
        GO_panel_dic = self.GO_ODF_dic[GO_panel_uid] = {}

        GO_panel_dic['_GO_uid'] = GO_panel_uid
        GO_panel_dic['Name'] = self.HW_ODF_get_attribute_value(HW_disp_page_dic, 'Name')
        GO_panel_dic['HasPedals'] = 'N'
        GO_panel_dic['NumberOfGUIElements'] = 0
        GO_panel_dic['NumberOfImages'] = 0

        if HW_page_id == self.HW_console_display_page_id:
            # the current HW DisplayPage object is the HW console page, get the dimensions of the console page defined in the HW _General object
            HW_general_dic = self.HW_ODF_get_object_dic('_General')
            GO_panel_dic['DispScreenSizeHoriz'] = myint(self.HW_ODF_get_attribute_value(HW_general_dic, 'Display_ConsoleScreenWidthPixels'))
            GO_panel_dic['DispScreenSizeVert'] = myint(self.HW_ODF_get_attribute_value(HW_general_dic, 'Display_ConsoleScreenHeightPixels'))
            GO_panel_dic['HasPedals'] = self.GO_ODF_dic['Organ']['HasPedals']  # value set before in GO_ODF_build_Manual_objects
        else:
            GO_panel_dic['DispScreenSizeHoriz'] = None  # will be set later while creating GO Panel999Image999 objects
            GO_panel_dic['DispScreenSizeVert'] = None   # will be set later while creating GO Panel999Image999 objects
            GO_panel_dic['HasPedals'] = 'N'

        # set the other mandatory attributes of a GO panel at a default value, no import from Hauptwerk ODF for the GO built-in console drawing
        GO_panel_dic['DispDrawstopBackgroundImageNum'] = '1'
        GO_panel_dic['DispDrawstopInsetBackgroundImageNum'] = '1'
        GO_panel_dic['DispConsoleBackgroundImageNum'] = '1'
        GO_panel_dic['DispKeyHorizBackgroundImageNum'] = '1'
        GO_panel_dic['DispKeyVertBackgroundImageNum'] = '1'
        GO_panel_dic['DispControlLabelFont'] = 'Arial'
        GO_panel_dic['DispShortcutKeyLabelFont'] = 'Arial'
        GO_panel_dic['DispShortcutKeyLabelColour'] = 'Black'
        GO_panel_dic['DispGroupLabelFont'] = 'Arial'
        GO_panel_dic['DispDrawstopCols'] = '2'
        GO_panel_dic['DispDrawstopRows'] = '1'
        GO_panel_dic['DispDrawstopColsOffset'] = 'N'
        GO_panel_dic['DispPairDrawstopCols'] = 'N'
        GO_panel_dic['DispExtraDrawstopRows'] = '0'
        GO_panel_dic['DispExtraDrawstopCols'] = '0'
        GO_panel_dic['DispButtonCols'] = '1'
        GO_panel_dic['DispExtraButtonRows'] = '0'
        GO_panel_dic['DispExtraPedalButtonRow'] = 'N'
        GO_panel_dic['DispButtonsAboveManuals'] = 'N'
        GO_panel_dic['DispExtraDrawstopRowsAboveExtraButtonRows'] = 'N'
        GO_panel_dic['DispTrimAboveManuals'] = 'N'
        GO_panel_dic['DispTrimBelowManuals'] = 'N'
        GO_panel_dic['DispTrimAboveExtraRows'] = 'N'

        # add in the HW DisplayPage object the ID of the corresponding GO object
        HW_disp_page_dic['_GO_uid'] = GO_panel_uid

        # build the GO static images of the panel by order of layer number
        HW_images_list_per_layer_dict = {}
        for HW_img_set_inst_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_page_dic, 'ImageSetInstance', TO_CHILD):
            # parse the HW ImageSetInstance objects of the given HW DisplayPage
            # to store in a local dictionary the static images of the given HW DisplayPage grouped by layer number
            if len(HW_img_set_inst_dic['_parents']) == 1:
                # the current HW ImageSetInstance object has a single parent (a DisplayPage) : it is a static image
                HW_layer_nb_int = myint(self.HW_ODF_get_attribute_value(HW_img_set_inst_dic, 'ScreenLayerNumber'))
                if HW_layer_nb_int == None:
                    # there is no layer defined, set by default the layer 1
                    HW_layer_nb_int = 1
                if HW_layer_nb_int not in HW_images_list_per_layer_dict.keys():
                    # there is not yet an entry in the dictionary for the layer number of the current HW ImageSetInstance
                    # add one entry initialized with an empty list
                    HW_images_list_per_layer_dict[HW_layer_nb_int] = []
                # add the current HW ImageSetInstance to the list of the layer numbers
                HW_images_list_per_layer_dict[HW_layer_nb_int].append(HW_img_set_inst_dic)
        for HW_layer_nb_int in sorted(HW_images_list_per_layer_dict.keys()):
            # parse the HW display layers by ascending order
            for HW_img_set_inst_dic in HW_images_list_per_layer_dict[HW_layer_nb_int]:
                # parse the HW ImageSetInstance objects of the current display layer
                self.GO_ODF_build_PanelImage_object(HW_img_set_inst_dic, GO_panel_dic)

        # build the GO labels of the panel
        for HW_text_inst_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_disp_page_dic, 'TextInstance', TO_CHILD):
            # parse the HW TextInstance objects of the given display page
            self.GO_ODF_build_PanelElement_Label_object(HW_text_inst_dic, GO_panel_dic)

        return GO_panel_dic

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_PanelImage_object(self, HW_img_set_inst_dic, GO_panel_dic):
        # build the GO Panel999Image999 object corresponding to the given HW ImageSetInstance and in the given GO Panel
        # return the dictionary of the created GO PaneL Image object, or None if no panel image created

        image_attr_dic = {}
        if self.HW_ODF_get_image_attributes(HW_img_set_inst_dic, image_attr_dic) and image_attr_dic['BitmapFilename'] != None:
            # the data about the current HW ImageSetInstance object have been recovered successfully and an image file name is defined

            if image_attr_dic['ImageWidthPixels'] == None or image_attr_dic['ImageHeightPixels'] == None:
                # if one dimension of the image is not defined, get the dimensions of the image in the bitmap file
                image_filename = os.path.dirname(self.HW_ODF_file_name_str) + '/' + image_attr_dic['BitmapFilename']
                image_filename = image_filename.replace('/', '\\')
                if os.path.isfile(image_filename):
                    im = Image.open(image_filename)
                    image_attr_dic['ImageHeightPixels'] = im.size[1]
                    image_attr_dic['ImageWidthPixels'] = im.size[0]
                else:
                    image_attr_dic['ImageHeightPixels'] = None
                    image_attr_dic['ImageWidthPixels'] = None

            # define an additional GO Panel999Image999 object for the given GO Panel
            GO_panel_uid = GO_panel_dic['_GO_uid']
            self.GO_ODF_dic[GO_panel_uid]['NumberOfImages'] += 1
            GO_panel_image_uid = GO_panel_uid + 'Image' + str(self.GO_ODF_dic[GO_panel_uid]['NumberOfImages']).zfill(3)
            GO_panel_image_dic = self.GO_ODF_dic[GO_panel_image_uid] = {}

            GO_panel_image_dic['PositionX'] = image_attr_dic['LeftXPosPixels']
            GO_panel_image_dic['PositionY'] = image_attr_dic['TopYPosPixels']
            GO_panel_image_dic['Width'] = image_attr_dic['ImageWidthPixels']
            GO_panel_image_dic['Height'] = image_attr_dic['ImageHeightPixels']
            GO_panel_image_dic['Image'] = image_attr_dic['BitmapFilename']
            if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
                GO_panel_image_dic['Mask'] = image_attr_dic['TransparencyMaskBitmapFilename']

            image_max_x_int = image_attr_dic['LeftXPosPixels'] + image_attr_dic['ImageWidthPixels']
            image_max_y_int = image_attr_dic['TopYPosPixels'] + image_attr_dic['ImageHeightPixels']

            # increase if necessary the GO panel dimensions to display entirely the added image
            if GO_panel_dic['DispScreenSizeHoriz'] == None or image_max_x_int > GO_panel_dic['DispScreenSizeHoriz']:
                GO_panel_dic['DispScreenSizeHoriz'] = image_max_x_int
            if GO_panel_dic['DispScreenSizeVert'] == None or image_max_y_int > GO_panel_dic['DispScreenSizeVert']:
                GO_panel_dic['DispScreenSizeVert'] = image_max_y_int

            # add in the HW ImageSetInstance object the ID of the corresponding GO object
            HW_img_set_inst_dic['_GO_uid'] = GO_panel_image_uid

            return GO_panel_image_dic
        else:
            return None

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_PanelElement_Label_object(self, HW_text_inst_dic, GO_panel_dic):
        # build the GO Panel999Element999 object (type Label) corresponding to the given HW TextInstance and in the given GO Panel
        # return the dictionary of the created GO Panel Element object, or None if no panel element created

        text_attr_dic = {}
        if self.HW_ODF_get_text_attributes(HW_text_inst_dic, text_attr_dic):
            # the data about the current HW TextInstance object (and his linked HW ImageSetInstance object if any) have been recovered successfully

            # define an additional GO Panel999Element999 object with label type in the given GO panel
            GO_panel_uid = GO_panel_dic['_GO_uid']
            self.GO_ODF_dic[GO_panel_uid]['NumberOfGUIElements'] += 1
            GO_panel_element_uid = GO_panel_uid + 'Element' + str(self.GO_ODF_dic[GO_panel_uid]['NumberOfGUIElements']).zfill(3)
            GO_panel_element_dic = self.GO_ODF_dic[GO_panel_element_uid] = {}

            GO_panel_element_dic['Type'] = 'Label'
            GO_panel_element_dic['Name'] = text_attr_dic['Text']

            # recover the display dimensions of the label text according to the font name/size/weight
            text_font = tkf.Font(family=text_attr_dic['Face_WindowsName'], size=-1 * text_attr_dic['Font_SizePixels'],
                                 weight='bold' if text_attr_dic['Font_WeightCode'] == 3 else 'normal')
            text_width = text_font.measure(text_attr_dic['Text'])
            text_height = text_font.metrics('ascent') + text_font.metrics('descent')

            if text_attr_dic['Font_SizePixels'] != None:
                GO_panel_element_dic['DispLabelFontSize'] = text_attr_dic['Font_SizePixels']
            else:
                GO_panel_element_dic['DispLabelFontSize'] = 10

            if text_attr_dic['Face_WindowsName'] != None:
                GO_panel_element_dic['DispLabelFontName'] = text_attr_dic['Face_WindowsName']

            if text_attr_dic['Colour_Red'] != None and text_attr_dic['Colour_Green'] != None and text_attr_dic['Colour_Blue'] != None:
                GO_panel_element_dic['DispLabelColour'] = '#%02x%02x%02x' % (text_attr_dic['Colour_Red'],
                                                                             text_attr_dic['Colour_Green'],
                                                                             text_attr_dic['Colour_Blue'])

            if text_attr_dic['ImageSetInstanceDic'] == None:
                # the text is not inside an image, use the default GO label background image (80x25)
                # the GO X,Y positions are the top left corner of the label background image

                # compute the coordinates of the center of the text according to the alignment of the text
                if text_attr_dic['HorizontalAlignmentCode'] == 0: # centered
                    xpos = text_attr_dic['XPosPixels']
                elif text_attr_dic['HorizontalAlignmentCode'] == 2: # right aligned
                    xpos = text_attr_dic['XPosPixels'] - int(text_width / 2)
                else:  # left aligned
                    xpos = text_attr_dic['XPosPixels'] + int(text_width / 2)

                if text_attr_dic['VerticalAlignmentCode'] == 0: # centered
                    ypos = text_attr_dic['YPosPixels']
                elif text_attr_dic['VerticalAlignmentCode'] == 2: # bottom aligned
                    ypos = text_attr_dic['YPosPixels'] - int(text_height / 2)
                else:  # top aligned
                    ypos = text_attr_dic['YPosPixels'] + int(text_height / 2)

                GO_panel_element_dic['DispImageNum'] = 3
                if xpos >= 40:
                    GO_panel_element_dic['DispXpos'] = xpos - 40  # 40 is the half width of the label image
                else:
                    GO_panel_element_dic['DispXpos'] = 0

                if ypos >= 13:
                    GO_panel_element_dic['DispYpos'] = ypos - 13      # 13 is the half height of the label image
                else:
                    GO_panel_element_dic['DispYpos'] = 0
            elif text_attr_dic['BitmapFilename'] != None:
                # the text is inside an image which is known
                # compute the coordinates of the text rectangle according to the alignment of the text
                if text_attr_dic['XPosPixels'] != None:
                    if text_attr_dic['HorizontalAlignmentCode'] == 0: # centered
                        xpos = text_attr_dic['XPosPixels'] - int(text_width / 2)
                    elif text_attr_dic['HorizontalAlignmentCode'] == 2: # right aligned
                        xpos = text_attr_dic['XPosPixels'] - text_width
                    else:  # left aligned
                        xpos = text_attr_dic['XPosPixels']
                    GO_panel_element_dic['TextRectLeft'] = str(xpos)
                    GO_panel_element_dic['TextRectWidth'] = str(text_width)

                if text_attr_dic['YPosPixels'] != None:
                    if text_attr_dic['VerticalAlignmentCode'] == 0: # centered
                        ypos = myint(text_attr_dic['YPosPixels']) - int(text_height / 2)
                    elif text_attr_dic['VerticalAlignmentCode'] == 2: # bottom aligned
                        ypos = myint(text_attr_dic['YPosPixels']) - text_height
                    else:  # top aligned
                        ypos = myint(text_attr_dic['YPosPixels'])
                    GO_panel_element_dic['TextRectTop'] = str(ypos)
                    GO_panel_element_dic['TextRectHeight'] = str(text_height)

                # manage the image attributes of the current HW TextInstance
##                if 'BitmapFilename' in text_attr_dic.keys() and text_attr_dic['BitmapFilename'] != None and text_attr_dic['InstallationPackageID'] != None:
                # the associated with this HW TextInstance is known
                GO_panel_element_dic['Image'] = text_attr_dic['BitmapFilename']

                if text_attr_dic['TransparencyMaskBitmapFilename'] != None:
                    GO_panel_element_dic['Mask'] = text_attr_dic['TransparencyMaskBitmapFilename']

                if text_attr_dic['LeftXPosPixels'] != None:
                    GO_panel_element_dic['PositionX'] = text_attr_dic['LeftXPosPixels']
                if text_attr_dic['TopYPosPixels'] != None:
                    GO_panel_element_dic['PositionY'] = text_attr_dic['TopYPosPixels']

                if text_attr_dic['ImageWidthPixels'] != None:
                    GO_panel_element_dic['Width'] = text_attr_dic['ImageWidthPixels']
                if text_attr_dic['ImageHeightPixels'] != None:
                    GO_panel_element_dic['Height'] = text_attr_dic['ImageHeightPixels']

                if text_attr_dic['BoundingBoxWidthPixelsIfWordWrap'] != None:
                    GO_panel_element_dic['TextRectWidth'] = str(int(text_attr_dic['BoundingBoxWidthPixelsIfWordWrap']) - 1)
                if text_attr_dic['BoundingBoxHeightPixelsIfWordWrap'] != None:
                    GO_panel_element_dic['TextRectHeight'] = text_attr_dic['BoundingBoxHeightPixelsIfWordWrap']

            # add in the HW TextInstance and ImageSetInstance objects the ID of the corresponding GO object
            HW_text_inst_dic['_GO_uid'] = GO_panel_element_uid
            if text_attr_dic['ImageSetInstanceDic'] != None:
                text_attr_dic['ImageSetInstanceDic']['_GO_uid'] = GO_panel_element_uid

            return GO_panel_element_dic
        else:
            return None

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Manual_object(self, HW_keyboard_key_dic):
        # build the GO Manual999 object based on the given HW Keyboard or HW KeyboardKey
        # keyboard_key  : seen in sample set Graboswki Ermelo, Paradisi Groningen/StMichel
        # keyboard only : seen in sample set Graboswki Ledziny/Skrzatusz, Augustine Dreischor/Lorris

        if HW_keyboard_key_dic['_HW_uid'][:-6] == 'KeyboardKey':
            # the given HW object is a KeyboardKey
            # get the HW Keyboard object to which belongs the given HW KeyboardKey
            HW_keyboard_dic = self.HW_ODF_get_object_dic_by_ref_id('Keyboard', HW_keyboard_key_dic, 'KeyboardID')
            keyboard_display_mode = 1  # the keyboard is graphically defined key by key
        elif HW_keyboard_key_dic['_HW_uid'][:-6] == 'Keyboard':
            # the given HW object is a Keyboard
            HW_keyboard_dic = HW_keyboard_key_dic
            keyboard_display_mode = 2  # the keyboard is graphically defined for one octave
        else:
            # wrong given HW object type
            self.events_log_add('INTERNAL ERROR : wrong object type provided to GO_ODF_build_Manual_object')
            return

        # get the HW Division to which belongs the given HW KeyboardKey
        HW_division_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_keyboard_dic, 'Division', TO_PARENT, True)
        if HW_division_dic == None:
            # cannot continue if the division ID is unknown
            self.events_log_add(f'INTERNAL ERROR : unable to know in which division is the keyboard {self.HW_ODF_get_attribute_value(HW_keyboard_dic, "Name")}')
            return False

        HW_division_id = int(HW_division_dic['_HW_uid'][-6:])

        # get the name of the HW Division, it will be the name of the GO Manual
        HW_keyboard_name_str = self.HW_ODF_get_attribute_value(HW_division_dic, 'Name')

        # define the GO Manual999 UID which will be associated to this HW Division
        GO_manual_uid = 'Manual' + str(HW_division_id - 1).zfill(3)
        if GO_manual_uid in self.GO_ODF_dic.keys():
            # the GO manual has been already created, we can exit
            return
        else:
            # add the GO Manual999 object in the GO ODF dictionary
            GO_manual_dic = self.GO_ODF_dic[GO_manual_uid] = {}
            GO_manual_dic['_GO_uid'] = GO_manual_uid
            if GO_manual_uid != 'Manual000':  # the Manual000 = Pedal is not counted
                self.GO_ODF_dic['Organ']['NumberOfManuals'] += 1

        # recover the first and last MIDI note numbers of the keyboard keys and the number of keys
        if keyboard_display_mode == 1:
            # recover this from the HW KeyboardKey objects belonging to the HW Keyboard
            first_midi_note_nb_int = 999
            last_midi_note_nb_int = 0
            nb_keys_int = 0
            keys_switch_dic = {}  # dictionnary with as key the MIDI note number and as value the corresponding HW Switch object
            for HW_keyboard_key_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_keyboard_dic, 'KeyboardKey', TO_CHILD):
                # parse the HW KeyboardKey objects which are children of the HW Keyboard
                # recover the HW ImageSetInstance associated to the HW Switch associated to the current HW KeyboardKey
                HW_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_keyboard_key_dic, 'SwitchID')
                HW_img_set_instance_id = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'Disp_ImageSetInstanceID'))
                if HW_img_set_instance_id != None:
                    # the current HW KeyboardKey has an associated HW ImageSetInstance (in Grabowski Enerlo the highest keys have no image)
                    nb_keys_int += 1
                    # get the MIDI note number of the current HW KeyboardKey object
                    midi_note_nb_int = myint(self.HW_ODF_get_attribute_value(HW_keyboard_key_dic, 'NormalMIDINoteNumber'))
                    if midi_note_nb_int == None: midi_note_nb_int = 60 # observed with Sound Paradisi sample sets, the MIDI note 60 is not defined
                    # update the first and last MIDI note numbers
                    if midi_note_nb_int < first_midi_note_nb_int: first_midi_note_nb_int = midi_note_nb_int
                    if midi_note_nb_int > last_midi_note_nb_int:  last_midi_note_nb_int = midi_note_nb_int
                    # add an entry in the keys switch dictionary with the HW Switch associated to the current HW KeyboardKey
                    keys_switch_dic[midi_note_nb_int] = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_keyboard_key_dic, 'SwitchID')
                    # add in the HW KeyboardKey object the UID of the corresponding GO object
                    HW_keyboard_key_dic['_GO_uid'] = GO_manual_uid
        else:
            nb_keys_int = int(self.HW_ODF_get_attribute_value(HW_keyboard_dic, 'KeyGen_NumberOfKeys'))
            first_midi_note_nb_int = myint(self.HW_ODF_get_attribute_value(HW_keyboard_dic, 'KeyGen_MIDINoteNumberOfFirstKey'))
            last_midi_note_nb_int = first_midi_note_nb_int + nb_keys_int - 1

        # get the HW DisplayPage in which is displayed the keyboard
        if keyboard_display_mode == 1:
            # recover this from the HW ImageSetInstance of the first key of the keyboard
            HW_img_set_instance_id = myint(self.HW_ODF_get_attribute_value(keys_switch_dic[first_midi_note_nb_int], 'Disp_ImageSetInstanceID', True))
            HW_img_set_instance_dic = self.HW_ODF_get_object_dic('ImageSetInstance', HW_img_set_instance_id)
            keyboard_disp_page_id = myint(self.HW_ODF_get_attribute_value(HW_img_set_instance_dic, 'DisplayPageID'))
        else:
            keyboard_disp_page_id = myint(self.HW_ODF_get_attribute_value(HW_keyboard_dic, 'KeyGen_DisplayPageID'))
        HW_disp_page_dic = self.HW_ODF_get_object_dic('DisplayPage', keyboard_disp_page_id)

        # get the corresponding GO Panel UID in which is displayed the keyboard
        GO_panel_uid = HW_disp_page_dic['_GO_uid']
        GO_panel_dic = self.GO_ODF_dic[GO_panel_uid]

        GO_manual_dic['Name'] = HW_keyboard_name_str
        GO_manual_dic['Displayed'] = 'Y'
        GO_manual_dic['NumberOfLogicalKeys'] = nb_keys_int
        GO_manual_dic['NumberOfAccessibleKeys'] = nb_keys_int
        GO_manual_dic['FirstAccessibleKeyLogicalKeyNumber'] = 1
        GO_manual_dic['FirstAccessibleKeyMIDINoteNumber'] = first_midi_note_nb_int
        GO_manual_dic['NumberOfStops'] = 0
        GO_manual_dic['NumberOfSwitches'] = 0
        GO_manual_dic['NumberOfCouplers'] = 0
        GO_manual_dic['NumberOfDivisionals'] = 0
        GO_manual_dic['NumberOfTremulants'] = 0
        # the manual display attributes will be put in the GO Manual999 by default
        GO_disp_manual_dic = GO_manual_dic

        if keyboard_disp_page_id != self.HW_default_display_page_id:
            # the keyboard is displayed in another display page than the default one
            # the GO Manual999 object must have Displayed = N
            # and its graphical attributes defined in a Panel999Element999 with Type = Manual and Displayed = Y
            GO_manual_dic['Displayed'] = 'N'

            # create a new GO Panel999Element999 object to display the keyboard
            self.GO_ODF_dic[GO_panel_uid]['NumberOfGUIElements'] += 1
            GO_panel_element_uid = GO_panel_uid + 'Element' + str(self.GO_ODF_dic[GO_panel_uid]['NumberOfGUIElements']).zfill(3)
            GO_panel_element_dic = self.GO_ODF_dic[GO_panel_element_uid] = {}

            GO_panel_element_dic['Type'] = 'Manual'
            #GO_panel_element_dic['Name'] = HW_keyboard_name_str  # attribute not used by GrandOrgue, so generating a warning in GO
            GO_panel_element_dic['Manual'] = GO_manual_uid[-3:]

            # the manual display attributes will be put in the GO Panel999Element999
            GO_disp_manual_dic = GO_panel_element_dic

        # define the graphical properties of the GO Manual
        if keyboard_display_mode == 1:
            # keys graphical aspect is defined for each key
            for midi_note_nb_int in range(first_midi_note_nb_int, last_midi_note_nb_int + 1):
                # parse the switches of the HW Keyboard by increasing MIDI note number
                GO_key_nb = midi_note_nb_int - first_midi_note_nb_int + 1

                if midi_note_nb_int < last_midi_note_nb_int:
                    # it is not the latest key of the keyboard
                    self.GO_ODF_build_Manual_keyimage_by_switch(keys_switch_dic[midi_note_nb_int], keys_switch_dic[midi_note_nb_int + 1], GO_disp_manual_dic, GO_key_nb)
                else:
                    self.GO_ODF_build_Manual_keyimage_by_switch(keys_switch_dic[midi_note_nb_int], None, GO_disp_manual_dic, GO_key_nb)

        else:
            # keys graphical aspect is defined for one octave + the first and last keys

            # get the HW KeyImageSet associated to the HW Keyboard
            HW_key_img_set_dic = self.HW_ODF_get_object_dic_by_ref_id('KeyImageSet', HW_keyboard_dic, 'KeyGen_KeyImageSetID')

            # set the GO Manual position
            GO_disp_manual_dic['PositionX'] = self.HW_ODF_get_attribute_value(HW_keyboard_dic, 'KeyGen_DispKeyboardLeftXPos')
            GO_disp_manual_dic['PositionY'] = self.HW_ODF_get_attribute_value(HW_keyboard_dic, 'KeyGen_DispKeyboardTopYPos')

            # set the GO Manual keys width
            GO_disp_manual_dic['Width_A']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfDASharpFromLeftOfDA')
            GO_disp_manual_dic['Width_Ais'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfEBFromLeftOfDASharp')
            GO_disp_manual_dic['Width_B']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')
            GO_disp_manual_dic['Width_C']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfCFSharpFromLeftOfCF')
            GO_disp_manual_dic['Width_Cis'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfDGFromLeftOfCFSharp')
            GO_disp_manual_dic['Width_D']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfDASharpFromLeftOfDA')
            GO_disp_manual_dic['Width_Dis'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfEBFromLeftOfDASharp')
            GO_disp_manual_dic['Width_E']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')
            GO_disp_manual_dic['Width_F']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfCFSharpFromLeftOfCF')
            GO_disp_manual_dic['Width_Fis'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfDGFromLeftOfCFSharp')
            GO_disp_manual_dic['Width_G']   = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfGSharpFromLeftOfG')
            GO_disp_manual_dic['Width_Gis'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfAFromLeftOfGSharp')

            # set the GO Manual keys offset
            GO_disp_manual_dic['Offset_A']   = '0'
            GO_disp_manual_dic['Offset_Ais'] = '0'
            GO_disp_manual_dic['Offset_B']   = '0'
            GO_disp_manual_dic['Offset_C']   = '0'
            GO_disp_manual_dic['Offset_Cis'] = '0'
            GO_disp_manual_dic['Offset_D']   = '0'
            GO_disp_manual_dic['Offset_Dis'] = '0'
            GO_disp_manual_dic['Offset_E']   = '0'
            GO_disp_manual_dic['Offset_F']   = '0'
            GO_disp_manual_dic['Offset_Fis'] = '0'
            GO_disp_manual_dic['Offset_G']   = '0'
            GO_disp_manual_dic['Offset_Gis'] = '0'

            # get the key up (not pressed) and key down (pressed) images index within image set if defined, else set default index
            key_up_img_index = myint(self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'ImageIndexWithinImageSets_Disengaged'))
            if key_up_img_index == None: key_up_img_index = 1
            HW_key_img_set_dic['_key_up_img_index'] = key_up_img_index

            key_down_img_index = myint(self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'ImageIndexWithinImageSets_Engaged'))
            if key_down_img_index == None: key_down_img_index = 2
            HW_key_img_set_dic['_key_down_img_index'] = key_down_img_index

            # set the GO Manual keys images
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'CF', GO_disp_manual_dic, 'C')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'CF', GO_disp_manual_dic, 'F')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'D', GO_disp_manual_dic, 'D')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'EB', GO_disp_manual_dic, 'E')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'EB', GO_disp_manual_dic, 'B')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'G', GO_disp_manual_dic, 'G')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'A', GO_disp_manual_dic, 'A')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'Sharp', GO_disp_manual_dic, 'Ais')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'Sharp', GO_disp_manual_dic, 'Cis')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'Sharp', GO_disp_manual_dic, 'Dis')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'Sharp', GO_disp_manual_dic, 'Fis')
            self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'Sharp', GO_disp_manual_dic, 'Gis')

            # set the GO Manual first key image and width
            first_note_name, octave = midi_number_to_note(int(first_midi_note_nb_int))
            if first_note_name == 'D':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'FirstKeyDA', GO_disp_manual_dic, 'FirstD')
                GO_disp_manual_dic['Width_FirstD'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfDASharpFromLeftOfDA')
            elif first_note_name == 'A':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'FirstKeyDA', GO_disp_manual_dic, 'FirstA')
                GO_disp_manual_dic['Width_FirstA'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfDASharpFromLeftOfDA')
            elif first_note_name == 'G':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'FirstKeyG', GO_disp_manual_dic, 'FirstG')
                GO_disp_manual_dic['Width_FirstG'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfGSharpFromLeftOfG')
            elif first_note_name == 'C':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'CF', GO_disp_manual_dic, 'FirstC')
                GO_disp_manual_dic['Width_FirstC'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfCFSharpFromLeftOfCF')

            # set the GO Manual last key image and width
            last_note_name, octave = midi_number_to_note(int(last_midi_note_nb_int))
            if last_note_name == 'D':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'LastKeyDG', GO_disp_manual_dic, 'LastD')
                GO_disp_manual_dic['Width_LastD'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')
            elif last_note_name == 'G':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'LastKeyDG', GO_disp_manual_dic, 'LastG')
                GO_disp_manual_dic['Width_LastG'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')
            elif last_note_name == 'A':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'LastKeyA', GO_disp_manual_dic, 'LastA')
                GO_disp_manual_dic['Width_LastA'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')
            elif last_note_name == 'C':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'WholeNatural', GO_disp_manual_dic, 'LastC')
                GO_disp_manual_dic['Width_LastC'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')
            elif last_note_name == 'F':
                self.GO_ODF_build_Manual_keyimage_by_keytype(HW_key_img_set_dic, 'WholeNatural', GO_disp_manual_dic, 'LastF')
                GO_disp_manual_dic['Width_LastF'] = self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'HorizSpacingPixels_LeftOfNaturalFromLeftOfNatural')

        # update in the GO Organ and Panel objects the HasPedal attribute value
        if GO_manual_uid == 'Manual000':
            self.GO_ODF_dic['Organ']['HasPedals'] = 'Y'
            GO_panel_dic['HasPedals'] = 'Y'

        # add in the HW Division and Keyboard objects the UID of the corresponding GO object
        HW_division_dic['_GO_uid'] = GO_manual_uid
        HW_keyboard_dic['_GO_uid'] = GO_manual_uid

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Manual_keyimage_by_keytype(self, HW_key_img_set_dic, HW_key_type, GO_disp_manual_dic, GO_key_type):
        # add to the given GO manual object ID the key images attributes of the given HW key type

        HW_image_set_id = myint(self.HW_ODF_get_attribute_value(HW_key_img_set_dic, 'KeyShapeImageSetID_' + HW_key_type))
        if HW_image_set_id != None:
            HW_image_set_dic = self.HW_ODF_get_object_dic('ImageSet', HW_image_set_id)

            # image for key up (not pressed)
            image_attr_dic = {}
            self.HW_ODF_get_image_attributes(HW_image_set_dic, image_attr_dic, HW_key_img_set_dic['_key_up_img_index'])
            if image_attr_dic['BitmapFilename'] != None:
                GO_disp_manual_dic['ImageOff_' + GO_key_type] = image_attr_dic['BitmapFilename']
            if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
                GO_disp_manual_dic['MaskOff_' + GO_key_type] = image_attr_dic['TransparencyMaskBitmapFilename']

            # image for key down (pressed)
            image_attr_dic = {}
            self.HW_ODF_get_image_attributes(HW_image_set_dic, image_attr_dic, HW_key_img_set_dic['_key_down_img_index'])
            if image_attr_dic['BitmapFilename'] != None:
                GO_disp_manual_dic['ImageOn_' + GO_key_type] = image_attr_dic['BitmapFilename']
            if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
                GO_disp_manual_dic['MaskOn_' + GO_key_type] = image_attr_dic['TransparencyMaskBitmapFilename']

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Manual_keyimage_by_switch(self, HW_switch_dic, HW_next_switch_dic, GO_disp_manual_dic, GO_key_nb):
        # add to the given GO manual object the key images attributes of the given HW Switch

        if HW_switch_dic == None: return

        HW_img_set_instance_id = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'Disp_ImageSetInstanceID', True))
        HW_img_set_instance_dic = self.HW_ODF_get_object_dic('ImageSetInstance', HW_img_set_instance_id)

        # get the key engaged and disengaged images indexes
        key_up_img_index = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'Disp_ImageSetIndexDisengaged', True))
        key_down_img_index = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'Disp_ImageSetIndexEngaged', True))

        # add in the HW Switch and ImageSetInstance objects the UID of the corresponding GO object
        HW_switch_dic['_GO_uid'] = GO_disp_manual_dic['_GO_uid']
        HW_img_set_instance_dic['_GO_uid'] = GO_disp_manual_dic['_GO_uid']

        key_nb_3digit_str = str(GO_key_nb).zfill(3)

        if GO_key_nb == 1:
            # set the GO keyboard position which is the position of the first key
            image_attr_dic = {}
            self.HW_ODF_get_image_attributes(HW_img_set_instance_dic, image_attr_dic, key_up_img_index)
            GO_disp_manual_dic['PositionX'] = image_attr_dic['LeftXPosPixels']
            GO_disp_manual_dic['PositionY'] = image_attr_dic['TopYPosPixels']

        # image for key up (not pressed)
        image_attr_dic = {}
        self.HW_ODF_get_image_attributes(HW_img_set_instance_dic, image_attr_dic, key_up_img_index)
        if image_attr_dic['BitmapFilename'] != None:
            GO_disp_manual_dic['Key' + key_nb_3digit_str + 'ImageOff'] = image_attr_dic['BitmapFilename']
        if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
            GO_disp_manual_dic['Key' + key_nb_3digit_str + 'MaskOff'] = image_attr_dic['TransparencyMaskBitmapFilename']

        # image for key down (pressed)
        image_attr_dic = {}
        self.HW_ODF_get_image_attributes(HW_img_set_instance_dic, image_attr_dic, key_down_img_index)
        if image_attr_dic['BitmapFilename'] != None:
            GO_disp_manual_dic['Key' + key_nb_3digit_str + 'ImageOn'] = image_attr_dic['BitmapFilename']
        if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
            GO_disp_manual_dic['Key' + key_nb_3digit_str + 'MaskOn'] = image_attr_dic['TransparencyMaskBitmapFilename']

        # width/offset of the key, width calculated by the diff of XPos of the key and its next one
        if HW_next_switch_dic != None:
            HW_next_img_set_instance_id = myint(self.HW_ODF_get_attribute_value(HW_next_switch_dic, 'Disp_ImageSetInstanceID', True))
            HW_next_img_set_instance_dic = self.HW_ODF_get_object_dic('ImageSetInstance', HW_next_img_set_instance_id)

            next_image_dic = {}
            self.HW_ODF_get_image_attributes(HW_next_img_set_instance_dic, next_image_dic, key_up_img_index)
            key_width = int(next_image_dic['LeftXPosPixels']) - int(image_attr_dic['LeftXPosPixels'])
            GO_disp_manual_dic['Key' + key_nb_3digit_str + 'Width'] = str(key_width)
            GO_disp_manual_dic['Key' + key_nb_3digit_str + 'Offset'] = '0'

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Stop_object(self, HW_ctrled_switch_dic, HW_ctrling_switch_dic_list):
        # build the GO Stop999 object controlled by the given control HW Switch (parent of a HW Stop) and by the displayed HW Switches (children of a HW DisplayPanel)
        # the two HW Switches can be the same object

        # get the HW Stop controlled by the given HW Switch object
        HW_stop_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_ctrled_switch_dic, 'Stop', TO_CHILD, True)

        # get the HW Division to which belongs the HW Stop
        HW_division_dic = self.HW_ODF_get_object_dic_by_ref_id('Division', HW_stop_dic, 'DivisionID')

        # get the GO Manual associated to the HW Division and so to the HW Stop
        if HW_division_dic['_GO_uid'] == '':
            # division not associated to a GO manual : it is a noise division, associate the stop to the GO Manual000
            GO_manual_dic = self.GO_ODF_dic['Manual000']
        else:
            GO_manual_dic = self.GO_ODF_dic[HW_division_dic['_GO_uid']]

        if HW_stop_dic['_GO_uid'] != '':
            # there is already a GO Stop associated with the given HW Stop
            GO_stop_uid = HW_stop_dic['_GO_uid']
            GO_stop_dic = self.GO_ODF_dic[GO_stop_uid]
        else:
            # create a new GO Stop999 object
            self.GO_objects_type_nb_dic['Stop'] += 1
            GO_stop_uid = 'Stop' + str(self.GO_objects_type_nb_dic['Stop']).zfill(3)
            GO_stop_dic = self.GO_ODF_dic[GO_stop_uid] = {}

            GO_stop_dic['Name'] = self.HW_ODF_get_attribute_value(HW_stop_dic, 'Name', True)
            GO_stop_dic['FirstAccessiblePipeLogicalKeyNumber'] = 0
            GO_stop_dic['NumberOfAccessiblePipes'] = 0
            GO_stop_dic['NumberOfRanks'] = 0

            manual_first_midi_note = GO_manual_dic['FirstAccessibleKeyMIDINoteNumber']
            manual_nb_keys = GO_manual_dic['NumberOfLogicalKeys']

            # associate ranks to the GO Stop object
            GO_stop_nb_ranks = 0
            for HW_stop_rank_dic in self.HW_ODF_get_linked_objects_dic_by_type(HW_stop_dic, 'StopRank', TO_CHILD):
                # parse the HW StopRank objects which are children of the HW Stop object

                # get the HW and GO Rank references corresponding to the current HW StopRank
                HW_rank_dic = self.HW_ODF_get_object_dic_by_ref_id('Rank', HW_stop_rank_dic, 'RankID')
                GO_rank_uid = HW_rank_dic['_GO_uid']
                if GO_rank_uid != '':
                    # the current HW Rank is associated to a GO Rank (may not be the case of some demo sample sets with empty HW ranks)
                    GO_rank_dic = self.GO_ODF_dic[GO_rank_uid]

                    # get the HW StopRank data
                    HW_action_type_code = myint(self.HW_ODF_get_attribute_value(HW_stop_rank_dic, 'ActionTypeCode'))
                    HW_action_effect_code = myint(self.HW_ODF_get_attribute_value(HW_stop_rank_dic, 'ActionEffectCode'))

                    HW_div_midi_note_first_mapped_input = myint(self.HW_ODF_get_attribute_value(HW_stop_rank_dic, 'MIDINoteNumOfFirstMappedDivisionInputNode'))
                    HW_div_midi_note_increment_to_rank = myint(self.HW_ODF_get_attribute_value(HW_stop_rank_dic, 'MIDINoteNumIncrementFromDivisionToRank'))
                    HW_div_nb_mapped_inputs = myint(self.HW_ODF_get_attribute_value(HW_stop_rank_dic, 'NumberOfMappedDivisionInputNodes'))
                    if HW_div_nb_mapped_inputs == None:
                        HW_div_nb_mapped_inputs = 61  # observed with Augustine Lorris sample set, this data is not defined for the HW Larigot stop

                    if HW_action_type_code == 1 and HW_action_effect_code == 1 and HW_div_nb_mapped_inputs > 0:
                        # action = Notes to notes: all notes played (normal), effect = Normal (sustain whilst held)
                        # it is a normal rank (not a noise rank)

                        # add a GO Rank to the GO Stop object correspondint to the current HW StopRank
                        GO_stop_nb_ranks += 1
                        GO_stop_dic['Rank' + str(GO_stop_nb_ranks).zfill(3)] = GO_rank_uid[-3:]

                        # convert the HW StopRank data into GO Stop data (for the current stop rank)
                        if HW_div_midi_note_increment_to_rank != None:
                            # there is a note increment between the manual key number and the rank pipe number
                            if HW_div_midi_note_first_mapped_input != None:
                                GO_rank_first_access_key_nb = HW_div_midi_note_first_mapped_input - manual_first_midi_note + 1
                                GO_stop_rank_first_pipe_nb = HW_div_midi_note_first_mapped_input + HW_div_midi_note_increment_to_rank - GO_rank_dic['FirstMidiNoteNumber'] + 1
                            else:
                                if HW_div_midi_note_increment_to_rank < 0:
                                    GO_rank_first_access_key_nb = 1 - HW_div_midi_note_increment_to_rank
                                else:
                                    GO_rank_first_access_key_nb = 1
                                GO_stop_rank_first_pipe_nb = GO_rank_first_access_key_nb + HW_div_midi_note_increment_to_rank
                        elif HW_div_midi_note_first_mapped_input != None:
                            GO_rank_first_access_key_nb = HW_div_midi_note_first_mapped_input - manual_first_midi_note + 1
                            GO_stop_rank_first_pipe_nb = HW_div_midi_note_first_mapped_input - GO_rank_dic['FirstMidiNoteNumber'] + 1
                        else:
                            GO_rank_first_access_key_nb = 1
                            GO_stop_rank_first_pipe_nb = 1

                        GO_stop_rank_pipe_count = HW_div_nb_mapped_inputs
                        if GO_rank_first_access_key_nb + GO_stop_rank_pipe_count -1 > manual_nb_keys:
                            # the rank range is going beyond manual highest key : reduce its number of accessible pipes
                            GO_stop_rank_pipe_count = manual_nb_keys - GO_rank_first_access_key_nb + 1

                        GO_stop_dic[f'Rank{str(GO_stop_nb_ranks).zfill(3)}FirstAccessibleKeyNumber'] = GO_rank_first_access_key_nb
                        GO_stop_dic[f'Rank{str(GO_stop_nb_ranks).zfill(3)}FirstPipeNumber'] = GO_stop_rank_first_pipe_nb
                        GO_stop_dic[f'Rank{str(GO_stop_nb_ranks).zfill(3)}PipeCount'] = GO_stop_rank_pipe_count

                        # add in the HW StopRank object the UID of the corresponding GO object
                        HW_stop_rank_dic['_GO_uid'] = GO_stop_uid

##                    elif HW_action_type_code == 21 and HW_action_effect_code == 1:
##                        # action = Stop switch action to one note (stop action noise/effect), effect = Normal (sustain whilst held)
##                        # it is a noise rank (like blower)
##                        GO_stop_nb_access_pipes = 0
##
##                    elif HW_action_type_code == 21 and HW_action_effect_code == 2:
##                        # action = Stop switch action to one note (stop action noise/effect), effect = Trigger percussively on downbeat
##                        # it is a stop engaging noise rank
##                        GO_stop_nb_access_pipes = 0
##
##                    elif HW_action_type_code == 21 and HW_action_effect_code == 3:
##                        # action = Stop switch action to one note (stop action noise/effect), effect = Trigger percussively on backbeat
##                        # it is a stop disengaging noise rank
##                        GO_stop_nb_access_pipes = 0
##
##                    else:
##                        # not supported kind of stop
##                        GO_stop_nb_access_pipes = 0

            # based on the Rank999xxx attributes created just before in the GO Stop for each HW StopRank, compute remaining attributes of the GO Stop
            GO_stop_first_access_key_nb = 999
            GO_stop_last_access_key_nb = 0
            for r in range(1, GO_stop_nb_ranks + 1):
                rank_first_key = GO_stop_dic[f'Rank{str(r).zfill(3)}FirstAccessibleKeyNumber']
                rank_last_key = rank_first_key + GO_stop_dic[f'Rank{str(r).zfill(3)}PipeCount'] - 1
                if GO_stop_first_access_key_nb > rank_first_key:
                    GO_stop_first_access_key_nb = rank_first_key
                if GO_stop_last_access_key_nb < rank_last_key:
                    GO_stop_last_access_key_nb = rank_last_key

            GO_stop_dic['FirstAccessiblePipeLogicalKeyNumber'] = GO_stop_first_access_key_nb
            GO_stop_dic['NumberOfAccessiblePipes'] = GO_stop_last_access_key_nb - GO_stop_first_access_key_nb + 1

            # adjust the Rank999FirstAccessibleKeyNumber attributes to be an offset compated to FirstAccessiblePipeLogicalKeyNumber
            for r in range(1, GO_stop_nb_ranks + 1):
                GO_stop_dic[f'Rank{str(r).zfill(3)}FirstAccessibleKeyNumber'] -= (GO_stop_dic['FirstAccessiblePipeLogicalKeyNumber'] - 1)

            if GO_stop_nb_ranks == 0 or GO_stop_dic['NumberOfAccessiblePipes'] == 0:
                # the HW Stop has none rank in it or no accessible pipes (case of demo sample sets or noise ranks), remove the entry in the dictionary
                del self.GO_ODF_dic[GO_stop_uid]
                self.GO_objects_type_nb_dic['Stop'] -= 1
                return

            GO_stop_dic['NumberOfRanks'] = GO_stop_nb_ranks
            GO_stop_dic['Function'] = 'And'
            GO_stop_dic['SwitchCount'] = 0

            # add the Stop to the GO Manual
            GO_manual_dic['NumberOfStops'] += 1
            GO_manual_dic['Stop' + str(GO_manual_dic['NumberOfStops']).zfill(3)] = GO_stop_uid[-3:]

            # add in the HW Stop object the UID of the corresponding GO object
            HW_stop_dic['_GO_uid'] = GO_stop_uid

        # create the GO Switch associated with the GO Stop
        GO_switch_uid = ''
        for HW_switch_dic in HW_ctrling_switch_dic_list:
            # parse the controlling HW Switch objects to create one GO Switch and if necessary several GO PanelElement switches
            # for each displayed HW Switch, all linked together for the same action on the controlled stop
            GO_switch_uid = self.GO_ODF_build_Switch_object(HW_switch_dic, GO_switch_uid)

        # add in the HW controled Switch object the ID of the corresponding GO object
        HW_ctrled_switch_dic['_GO_uid'] = GO_switch_uid

        # add the created Switch to the GO Stop
        GO_stop_dic['SwitchCount'] += 1
        GO_stop_dic['Switch' + str(GO_stop_dic['SwitchCount']).zfill(3)] = GO_switch_uid[-3:]

        # add the Switch to the current GO Manual
        GO_manual_dic['NumberOfSwitches'] += 1
        GO_manual_dic['Switch' + str(GO_manual_dic['NumberOfSwitches']).zfill(3)] = GO_switch_uid[-3:]

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Coupler_object(self, HW_ctrled_switch_dic, HW_ctrling_switch_dic_list):
        # build the GO Coupler999 object associated to the given control (parent of a KeyAction) and display (child of a DisplayPanel) HW Switches
        # the two HW Switches can be the same objects in some sample sets

        # get the HW KeyAction controlled by the given HW Switch object
        HW_key_action_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_ctrled_switch_dic, 'KeyAction', TO_CHILD, True)
        if HW_key_action_dic['_GO_uid'] != '':
            # there is already a GO Coupler associated with the given HW KeyAction
            GO_coupler_uid = HW_key_action_dic['_GO_uid']
            GO_coupler_dic = self.GO_ODF_dic[GO_coupler_uid]
        else:
            # get the source division of the HW KeyAction
            HW_source_keyboard_dic = self.HW_ODF_get_object_dic_by_ref_id('Keyboard', HW_key_action_dic, 'SourceKeyboardID')
            HW_source_division_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_source_keyboard_dic, 'Division', TO_PARENT, True)

            # get the destination division of the HW KeyAction
            HW_dest_division_dic = self.HW_ODF_get_object_dic_by_ref_id('Division', HW_key_action_dic, 'DestDivisionID')
            if HW_dest_division_dic == None:
                HW_dest_keyboard_dic = self.HW_ODF_get_object_dic_by_ref_id('Keyboard', HW_key_action_dic, 'DestKeyboardID')
                if HW_dest_keyboard_dic != None:
                    HW_dest_division_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_dest_keyboard_dic, 'Division', TO_PARENT, True)

            if HW_source_division_dic == None or HW_dest_division_dic == None:
                self.events_log_add(f'INTERNAL ERROR : unable to find the HW source/destination divisions of the KeyAction {self.HW_ODF_get_attribute_value(HW_key_action_dic, "Name")}')
                return

            # get the corresponding GO source and destination Manual UID
            GO_source_manual_uid = HW_source_division_dic['_GO_uid']
            GO_dest_manual_uid = HW_dest_division_dic['_GO_uid']

            if GO_source_manual_uid == '' or GO_dest_manual_uid == '':
                self.events_log_add(f'INTERNAL ERROR : unable to find the GO source/destination manuals of the KeyAction {self.HW_ODF_get_attribute_value(HW_key_action_dic, "Name")}')
                return

            # create a GO Coupler999 object
            self.GO_objects_type_nb_dic['Coupler'] += 1
            GO_coupler_uid = 'Coupler' + str(self.GO_objects_type_nb_dic['Coupler']).zfill(3)
            GO_coupler_dic = self.GO_ODF_dic[GO_coupler_uid] = {}

            GO_coupler_dic['Name'] = self.HW_ODF_get_attribute_value(HW_key_action_dic, 'Name')
            GO_coupler_dic['UnisonOff'] = 'N'
            GO_coupler_dic['Displayed'] = 'N'
            GO_coupler_dic['DestinationManual'] = GO_dest_manual_uid[-3:]
            GO_coupler_dic['DestinationKeyshift'] = 0
            GO_coupler_dic['NumberOfKeys'] = myint(self.HW_ODF_get_attribute_value(HW_key_action_dic, 'NumberOfKeys'))
            GO_coupler_dic['CoupleToSubsequentUnisonIntermanualCouplers'] = 'N'
            GO_coupler_dic['CoupleToSubsequentUpwardIntermanualCouplers'] = 'N'
            GO_coupler_dic['CoupleToSubsequentDownwardIntermanualCouplers'] = 'N'
            GO_coupler_dic['CoupleToSubsequentUpwardIntramanualCouplers'] = 'N'
            GO_coupler_dic['CoupleToSubsequentDownwardIntramanualCouplers'] = 'N'
            GO_coupler_dic['Function'] = 'And'
            GO_coupler_dic['SwitchCount'] = 0

            # add the coupler in the GO source manual
            GO_source_manual_dic = self.GO_ODF_dic[GO_source_manual_uid]
            GO_source_manual_dic['NumberOfCouplers'] += 1
            GO_source_manual_dic['Coupler' + str(GO_source_manual_dic['NumberOfCouplers']).zfill(3)] = GO_coupler_uid[-3:]

            # add in the HW KeyAction object the UID of the corresponding GO object
            HW_key_action_dic['_GO_uid'] = GO_coupler_uid

        GO_switch_uid = ''
        for HW_switch_dic in HW_ctrling_switch_dic_list:
            # parse the controlling HW Switch objects to create one GO Switch and if necessary several GO PanelElement switches
            # for each displayed HW Switch, all linked together for the same action on the controlled stop
            GO_switch_uid = self.GO_ODF_build_Switch_object(HW_switch_dic, GO_switch_uid)

##        # get the HW Switch controlling the given HW KeyAction
##        HW_ctrl_switch_dic = self.HW_ODF_get_object_dic_by_ref_id('Switch', HW_key_action_dic, 'ConditionSwitchID')
##        if HW_ctrl_switch_dic['_GO_uid'] != '':
##            # there is already a GO Switch associated with the HW Switch controlling the given HW KeyAction
##            GO_switch_uid = HW_ctrl_switch_dic['_GO_uid']
##            GO_switch_dic = self.GO_ODF_dic[GO_switch_uid]
##            # create a GO Switch linked with the existing one
##            GO_switch_uid = self.GO_ODF_build_Switch_object(HW_disp_switch_dic, GO_switch_uid)
##
##        else:
##            # create a GO Switch999 object using the attributes of the given displayed HW Switch
##            GO_switch_uid = self.GO_ODF_build_Switch_object(HW_disp_switch_dic)
##            # add in the HW control Switch object the ID of the corresponding GO object
##            HW_ctrl_switch_dic['_GO_uid'] = GO_switch_uid

        # add the created Switch to the GO Coupler
        GO_coupler_dic['SwitchCount'] += 1
        GO_coupler_dic['Switch' + str(GO_coupler_dic['SwitchCount']).zfill(3)] = GO_switch_uid[-3:]

        # add the Switch to the source GO Manual
        GO_source_manual_dic['NumberOfSwitches'] += 1
        GO_source_manual_dic['Switch' + str(GO_source_manual_dic['NumberOfSwitches']).zfill(3)] = GO_switch_uid[-3:]

    #-------------------------------------------------------------------------------------------------
    def GO_ODF_build_Switch_object(self, HW_switch_dic, linked_GO_switch_uid = ''):
        # add a GO Switch with the properties of the given HW Switch object, only if it is has graphical properties and is not a key switch
        # link it to the given existing GO Switch if provided (case of switch not in the default panel)
        # return the UID of the added GO Switch or of the linked GO Switch if provided

        # get the HW ImageSetInstance object associated to the given HW Switch object if any
        HW_img_set_inst_dic = self.HW_ODF_get_object_dic_by_ref_id('ImageSetInstance', HW_switch_dic, 'Disp_ImageSetInstanceID')
        # get the ID of the HW display page in which the switch is displayed if any
        HW_switch_disp_page_id = myint(self.HW_ODF_get_attribute_value(HW_img_set_inst_dic, 'DisplayPageID', True))
        # get the HW KeyboardKey children object of the given HW Switch object if any
        HW_keyboard_key_dic = self.HW_ODF_get_linked_objects_dic_by_type(HW_switch_dic, 'KeyboardKey', TO_CHILD, True)

        if HW_img_set_inst_dic == None or HW_keyboard_key_dic != None or HW_switch_disp_page_id == None:
            # this HW Switch object is not referencing a HW ImageSetInstance object or is linked to a HW KeyboardKey object or has no display page ID
            # the HW switches which are not visible or which are used for keyboard keys are not converted into GO switches
            GO_switch_uid = linked_GO_switch_uid
            return GO_switch_uid

        # determine which switch configuration to manage
        switch_config = 0
        if HW_switch_disp_page_id == self.HW_default_display_page_id:
            # the switch is located in the default display page / panel
            if linked_GO_switch_uid == '':
                switch_config = 1 # new Switch999 to display in the default panel
            else:
                switch_config = 2 # existing Switch999 to overwrite in the default panel
                return ''
        else:
            if linked_GO_switch_uid == '':
                switch_config = 3 # new Panel999Element999 switch to display in another panel, linked to a new Switch999
            else:
                switch_config = 4 # new Panel999Element999 switch to display in another panel, linked to the given Switch999

        switch_name = self.HW_ODF_get_attribute_value(HW_switch_dic, 'Name')

        if switch_config in (1, 3):
            # new GO Switch999 to create
            self.GO_ODF_dic['Organ']['NumberOfSwitches'] += 1
            GO_switch_uid = 'Switch' + str(self.GO_ODF_dic['Organ']['NumberOfSwitches']).zfill(3)
            GO_switch_dic = self.GO_ODF_dic[GO_switch_uid] = {}

            GO_switch_dic['Name'] = switch_name

            GO_switch_dic['Displayed'] = 'N'

            if self.HW_ODF_get_attribute_value(HW_switch_dic, 'DefaultToEngaged') != None:
                GO_switch_dic['DefaultToEngaged'] = self.HW_ODF_get_attribute_value(HW_switch_dic, 'DefaultToEngaged')
            else:
                GO_switch_dic['DefaultToEngaged'] = 'N'

        else:  # switch config 2 or 4
            # no new GO Switch999 to create, we use the UID of the given linked switch
            GO_switch_uid = linked_GO_switch_uid
            GO_switch_dic = self.GO_ODF_dic[GO_switch_uid]

        if switch_config in (3, 4):
            # new GO Panel999Element999 switch object to create
            # recover the GO panel UID corresponding to the HW display page ID of the switch
            HW_disp_page_dic = self.HW_ODF_get_object_dic('DisplayPage', HW_switch_disp_page_id)
            GO_panel_uid = HW_disp_page_dic['_GO_uid']
            # create a new GO Panel999Element999 switch object to display the switch in it
            self.GO_ODF_dic[GO_panel_uid]['NumberOfGUIElements'] += 1
            GO_panel_element_uid = GO_panel_uid + 'Element' + str(self.GO_ODF_dic[GO_panel_uid]['NumberOfGUIElements']).zfill(3)
            GO_panel_element_dic = self.GO_ODF_dic[GO_panel_element_uid] = {}

            GO_panel_element_dic['Type'] = 'Switch'
            #GO_panel_element_dic['Name'] = switch_name   # attribute not used by GrandOrgue, so generating a warning in GO
            GO_panel_element_dic['Switch'] = GO_switch_uid[-3:]

            # the graphical attributes will be writen in the panel element object
            GO_disp_switch_dic = GO_panel_element_dic
        else:
            # the graphical attributes will be writen in the switch object
            GO_disp_switch_dic = GO_switch_dic
            GO_disp_switch_dic['Displayed'] = 'Y'

        # define the graphical attributes of the GO switch (which is a Switch999 or Panel999Element999 switch object)
        GO_disp_switch_dic['DispLabelText'] = ''

        # get the index of the switch image for OFF and ON positions
        switch_off_img_index = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'Disp_ImageSetIndexDisengaged'))
        switch_on_img_index = myint(self.HW_ODF_get_attribute_value(HW_switch_dic, 'Disp_ImageSetIndexEngaged'))
        if switch_off_img_index == None: switch_off_img_index = '1'
        if switch_on_img_index == None: switch_on_img_index = '1'

        # set the attributes of the switch OFF image
        image_attr_dic = {}
        self.HW_ODF_get_image_attributes(HW_img_set_inst_dic, image_attr_dic, switch_off_img_index)
        GO_disp_switch_dic['PositionX'] = image_attr_dic['LeftXPosPixels']
        GO_disp_switch_dic['PositionY'] = image_attr_dic['TopYPosPixels']
        if image_attr_dic['ImageWidthPixels'] != None:
            GO_disp_switch_dic['Width'] = image_attr_dic['ImageWidthPixels']
        if image_attr_dic['ImageHeightPixels'] != None:
            GO_disp_switch_dic['Height'] = image_attr_dic['ImageHeightPixels']

        # set the mouse clickable area
        if image_attr_dic['ClickableAreaLeftRelativeXPosPixels'] != None:
            GO_disp_switch_dic['MouseRectLeft'] = image_attr_dic['ClickableAreaLeftRelativeXPosPixels']
        if image_attr_dic['ClickableAreaTopRelativeYPosPixels'] != None:
            GO_disp_switch_dic['MouseRectTop'] = image_attr_dic['ClickableAreaTopRelativeYPosPixels']
        if image_attr_dic['ClickableAreaRightRelativeXPosPixels'] != None:
            GO_disp_switch_dic['MouseRectWidth'] = image_attr_dic['ClickableAreaRightRelativeXPosPixels']
        if image_attr_dic['ClickableAreaBottomRelativeYPosPixels'] != None:
            GO_disp_switch_dic['MouseRectHeight'] = image_attr_dic['ClickableAreaBottomRelativeYPosPixels']
        GO_disp_switch_dic['MouseRadius'] = 0

        if image_attr_dic['BitmapFilename'] != None:
            GO_disp_switch_dic['ImageOff'] = image_attr_dic['BitmapFilename']
        if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
            GO_disp_switch_dic['MaskOff'] = image_attr_dic['TransparencyMaskBitmapFilename']

        # set the attributes of the switch ON image
        image_attr_dic = {}
        self.HW_ODF_get_image_attributes(HW_img_set_inst_dic, image_attr_dic, switch_on_img_index)
        if image_attr_dic['BitmapFilename'] != None:
            GO_disp_switch_dic['ImageOn'] = image_attr_dic['BitmapFilename']
        if image_attr_dic['TransparencyMaskBitmapFilename'] != None:
            GO_disp_switch_dic['MaskOn'] = image_attr_dic['TransparencyMaskBitmapFilename']

        # add in the HW Switch object the ID of the corresponding GO object
        if switch_config in (3, 4):
            HW_img_set_inst_dic['_GO_uid'] = GO_panel_element_uid
        else:
            HW_img_set_inst_dic['_GO_uid'] = GO_switch_uid

        # add in the HW Switch object the ID of the corresponding GO object
        HW_switch_dic['_GO_uid'] = GO_switch_uid

        return GO_switch_uid

    #-------------------------------------------------------------------------------------------------
    def convert_file_name(self, file_name_str, install_package_id):
        # return the file path (for images or sounds or info files) converted from HW to GO format
        # in GO format the files path starts from the ODF location which is in the HW folder OrganDefinitions, whereas the files are in the HW folder OrganInstallationPackages \ PackageID on 6 digits
        # return None if the given package ID is not present in the sample set of the loaded HW ODF

        if install_package_id in self.HW_packages_id_list:
            file_name_str = '..\\OrganInstallationPackages\\' + str(install_package_id).zfill(6) + '\\' + file_name_str
            return file_name_str.replace('/', '\\')
        else:
            # unavailable package
            return None

    #-------------------------------------------------------------------------------------------------
    def events_log_add(self, log_string):
        #--- add the given string to the events log list

        self.events_log_list.append(log_string)

    #-------------------------------------------------------------------------------------------------
    def events_log_clear(self):
        #--- clear the events log list

        self.events_log_list.clear()

#-------------------------------------------------------------------------------------------------
class C_GUI():
    #--- class to manage the graphical user interface of the application

    odf_data = None             # one instance of the C_ODF class
    odf_conv = None             # one instance of the C_HW2GO class
    selected_object_UID = ''     # ID of the object currently selected in the objects list or tree widgets
    selected_object_type = ''   # type of the object currently selected : 'GO' or 'HW'
    data_changed = False        # flag indicating that data have been changed in the odf_data and not saved in an ODF
    object_edited = False       # flag indicating that the data of an object have been edited (and not yet applied in odf_data)s
    gui_events_blocked = False  # flag indicating that the GUI events are currently blocked
    text_in_search = ''         # text which is currently in search in the help
    search_index = ''           # last search result position in the help

    tag_field = "tag_field"     # tag to identify the syntax color for the fields
    tag_comment = "tag_comment" # tag to identify the syntax color for the comments
    tag_obj_UID = "tag_obj_UID"   # tag to identify the syntax color for the object IDs
    tag_title = "tag_title"     # tag to identify the syntax color for the titles in the help
    tag_found = "tag_found"     # tag to identify the syntax color for the string found by the search in the help

    #-------------------------------------------------------------------------------------------------
    def wnd_main_build(self):
        #--- build the main window of the application with all his GUI widgets

        #--- create an instance of the C_ODF class
        self.odf_data = C_ODF()

        #--- create an instance of the C_HW2GO class
        self.odf_conv = C_HW2GO()

        #--- create the main window
        self.wnd_main = Tk(className='OdfEdit')
        self.wnd_main.title(MAIN_WINDOW_TITLE)
        self.wnd_main.geometry('1600x800')
        self.wnd_main.bind('<Configure>', self.wnd_main_configure) # to adjust the widgets size on main windows resizing
        self.wnd_main.protocol("WM_DELETE_WINDOW", self.wnd_main_quit) # to ask the user to save his changed before to close the main window
        # assign an image to the main window icon
        icon = PhotoImage(file = os.path.dirname(__file__) + '/OdfEdit.png')
        self.wnd_main.iconphoto(False, icon)

        #--- define the styles of some widgets
        ttk.Style().theme_use('clam')
        ttk.Style().configure("Treeview", highlightthickness=3, font=('Calibri', 11), foreground="black")
        ttk.Style().configure("TNotebook.Tab", font=('Calibri', 11), foreground="black")
        self.wnd_main.option_add("*TCombobox*Listbox*Background", 'white')
        self.wnd_main.option_add("*TCombobox*Listbox*Foreground", 'black')

        #--- create the various widgets inside the main window

        # button "New"
        self.btn_odf_new = Button(self.wnd_main, text="New", fg="black", command=self.file_new)
        self.btn_odf_new.place(x=10, y=10, width=70, height=20)

        # button "Open"
        self.btn_odf_file_open = Button(self.wnd_main, text="Open", fg="black", command=self.file_open)
        self.btn_odf_file_open.place(x=90, y=10, width=70, height=20)
        CreateToolTip(self.btn_odf_file_open, "To open a GrandOrgue ODF (extension .organ) or a Hauptwerk ODF (extension .Organ_Hauptwerk_xml).")

        # button "Save"
        self.btn_odf_file_save = Button(self.wnd_main, text="Save", fg="black", state=DISABLED, command=self.file_save)
        self.btn_odf_file_save.place(x=170, y=10, width=80, height=20)

        # button "Save as..."
        self.btn_odf_file_saveas = Button(self.wnd_main, text="Save as...", fg="black", state=DISABLED, command=self.file_saveas)
        self.btn_odf_file_saveas.place(x=260, y=10, width=80, height=20)

        # button "Quit"
        self.btn_quit_appli = Button(self.wnd_main, text="Quit", fg="black", command=self.wnd_main_quit)
        self.btn_quit_appli.place(x=960, y=10, width=70, height=20)

        # button "Apply changes"
        self.btn_object_apply_chg = Button(self.wnd_main, text="Apply changes", fg="black", state=DISABLED, command=self.object_text_apply_chg)
        self.btn_object_apply_chg.place(x=530, y=45, width=100, height=20)
        CreateToolTip(self.btn_object_apply_chg, "Apply the changes dones in the text box below in the selected object or create a new object if the object ID is different.")

        # button "Delete"
        self.btn_object_delete = Button(self.wnd_main, text="Delete", fg="black", state=DISABLED, command=self.object_text_delete)
        self.btn_object_delete.place(x=640, y=45, width=100, height=20)
        CreateToolTip(self.btn_object_delete, "Delete the selected object.")

        # button "Do checks"
        self.btn_data_check = Button(self.wnd_main, text="Do checks", fg="black", state=DISABLED, command=self.check_odf_lines)
        self.btn_data_check.place(x=790, y=45, width=100, height=20)
        CreateToolTip(self.btn_data_check, "Execute checks in the loaded ODF data (syntax, compliance with the specification).")

        # button "Show in help"
        self.btn_show_help = Button(self.wnd_main, text="Show in help", fg="black", state=DISABLED, command=self.help_selected_object)
        self.btn_show_help.place(x=930, y=45, width=100, height=20)
        CreateToolTip(self.btn_show_help, "Show in the help tab the part describing the selected object.")

        # button "Collapse all" for the objects tree
        self.btn_collapse_all = Button(self.wnd_main, text="Collapse all", fg="black", state=DISABLED, command=self.objects_tree_collapse_all)
        self.btn_collapse_all.place(x=310, y=45, width=80, height=20)

        # button "Expand all" for the objects tree
        self.btn_expand_all = Button(self.wnd_main, text="Expand all", fg="black", state=DISABLED, command=self.objects_tree_expand_all)
        self.btn_expand_all.place(x=400, y=45, width=80, height=20)

        # label with loaded ODF file name
        self.lab_odf_file_name = Label(self.wnd_main, text="", fg="black", borderwidth=1, relief="solid", anchor=E)
        self.lab_odf_file_name.place(x=350, y=10, width=600, height=20)

        # label with the number of objects in the objects list
        self.lab_objects_nb = Label(self.wnd_main, text="", fg="black", borderwidth=0, relief="solid", anchor=CENTER)
        self.lab_objects_nb.place(x=10, y=50, width=250, height=20)

        # label with the number and list of parents of the selected object ID
        self.lab_parents_list = Label(self.wnd_main, text="", fg="black", borderwidth=0, relief="solid", anchor=NW, wraplength=500)
        self.lab_parents_list.place(x=530, y=70, width=500, height=30)

        # list box with objects IDs and names, with horizontal and vertical scroll bars
        # a frame is used to encapsulate the list box and scroll bars to facilitate their resizing
        self.frm_object_list = Frame(self.wnd_main)
        self.frm_object_list.place(x=10, y=70, width=250, height=520)
        scrollbarv = ttk.Scrollbar(self.frm_object_list, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh = ttk.Scrollbar(self.frm_object_list, orient='horizontal')
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.lst_objects_list = Listbox(self.frm_object_list, bg='white', font='Calibri 11', fg="black", exportselection=0, selectmode='single', activestyle='none')
        self.lst_objects_list.pack(side=LEFT, fill=BOTH, expand=True)
        self.lst_objects_list.bind('<<ListboxSelect>>', self.objects_list_selected)
        self.lst_objects_list.config(yscrollcommand=scrollbarv.set)
        self.lst_objects_list.config(xscrollcommand=scrollbarh.set)
        scrollbarv.config(command=self.lst_objects_list.yview)
        scrollbarh.config(command=self.lst_objects_list.xview)

        # treeview to display the objects hierarchy, with horizontal and vertical scroll bars
        # a frame is used to encapsulate the tree box and scroll bar to facilitate their resizing
        self.frm_object_tree = Frame(self.wnd_main)
        self.frm_object_tree.place(x=270, y=70, width=250, height=520)
        scrollbarv = ttk.Scrollbar(self.frm_object_tree, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh = ttk.Scrollbar(self.frm_object_tree, orient='horizontal')
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.trv_objects_tree = ttk.Treeview(self.frm_object_tree, show="tree", selectmode='browse') #, style="myTVstyle.Treeview")
        self.trv_objects_tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.trv_objects_tree.column('#0', width=500)
        self.trv_objects_tree.bind('<<TreeviewSelect>>', self.objects_tree_selected)
        self.trv_objects_tree.config(yscrollcommand=scrollbarv.set)
        self.trv_objects_tree.config(xscrollcommand=scrollbarh.set)
        scrollbarv.config(command=self.trv_objects_tree.yview)
        scrollbarh.config(command=self.trv_objects_tree.xview)

        # text box to edit the data of an object, with vertical and horizontal scroll bars
        # a frame is used to encapsulate the text box and scroll bars
        self.frm_object_text = Frame(self.wnd_main)
        self.frm_object_text.place(x=530, y=100, width=500, height=490)
        scrollbarv = ttk.Scrollbar(self.frm_object_text, orient='vertical')
        scrollbarh = ttk.Scrollbar(self.frm_object_text, orient='horizontal')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.txt_object_text = Text(self.frm_object_text, fg="black", bg='white', bd=3, wrap="none", font="Calibri 11", selectbackground="snow3", undo=True)
        self.txt_object_text.pack(side=LEFT, fill=BOTH, expand=True)
        self.txt_object_text.bind('<<Modified>>', self.object_text_changed)
        self.txt_object_text.bind('<KeyRelease>', self.object_text_key_pressed)
        self.txt_object_text.config(xscrollcommand=scrollbarh.set, yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.txt_object_text.yview)
        scrollbarh.config(command=self.txt_object_text.xview)
        # create a context menu
        self.txt_object_text.bind("<Button-3>", self.object_text_context_menu)
        self.obj_txt_menu = Menu(self.txt_object_text, tearoff=0)
        self.obj_txt_menu.add_command(label="Clear all", command=self.object_text_clear)
        # define the tags for the syntax highlighting
        self.txt_object_text.tag_config(self.tag_field, foreground='red3')
        self.txt_object_text.tag_config(self.tag_comment, foreground='chartreuse4')
        self.txt_object_text.tag_config(self.tag_obj_UID, foreground='blue2', font='Calibri 11 bold')

        # notebook to display the events logs or the help
        self.notebook = ttk.Notebook(self.wnd_main)
        self.notebook.place(x=1040, y=10, width=550, height=580)

        # text box to display the application events logs in the notebook, with horizontal/vertical scroll bars
        # a frame is used to encapsulate the text box and scroll bars
        self.frm_logs = Frame(self.notebook)
        self.frm_logs.pack(fill=BOTH, expand=True)
        scrollbarv = ttk.Scrollbar(self.frm_logs, orient='vertical')
        scrollbarh = ttk.Scrollbar(self.frm_logs, orient='horizontal')
        scrollbarv.pack(side=RIGHT, fill=Y)
        scrollbarh.pack(side=BOTTOM, fill=X)
        self.txt_events_log = Text(self.frm_logs, fg="black", bg='ivory2', bd=3, wrap="none", font='Calibri 11', selectbackground="grey")
        self.txt_events_log.pack(side=LEFT, fill=BOTH, expand=True)
        self.txt_events_log.config(xscrollcommand=scrollbarh.set, yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.txt_events_log.yview)
        scrollbarh.config(command=self.txt_events_log.xview)
        # create a context menu
        self.txt_events_log.bind("<Button-3>", self.events_log_text_context_menu)
        self.logs_txt_menu = Menu(self.txt_events_log, tearoff=0)
        self.logs_txt_menu.add_command(label="Clear all", command=self.events_log_text_clear)

        # text box to display the help in the notebook, with vertical scroll bar and search widgets
        # a main frame is used to encapsulate two other frames, one for the search widgets, one for the text box and his scroll bar
        self.frm_help = Frame(self.notebook)
        self.frm_help.pack(fill=BOTH, expand=True)
        # widgets to search a text
        self.frm_help_search = Frame(self.frm_help)
        self.frm_help_search.place(x=0, y=0, height=30, relwidth=1.0)
        self.lab_search = Label(self.frm_help_search, text="Search :", fg="black", borderwidth=0, relief="solid", anchor=E)
        self.lab_search.place(x=10, y=5, width=60, height=20)
        self.cmb_search_text = ttk.Combobox(self.frm_help_search, height=24, values=['[Organ]', '[Button]', '[Coupler999]', '[Divisional999]', '[DivisionalCoupler999]', '[DrawStop]', '[Enclosure999]', '[General999]', '[Image999]', '[Label999]', '[Manual999]', '[Panel999]', '[Panel999Element999]', '[Panel999Image999]', '[Panel999xxxxx999]', '[Piston]', '[PushButton]', '[Rank999]', '[ReversiblePiston999]', '[SetterElement999]', '[Stop999]', '[Switch999]', '[Tremulant999]', '[WindchestGroup999]'])
        self.cmb_search_text.place(x=80, y=5, width=170, height=20)
        self.cmb_search_text.bind('<KeyRelease>', self.help_search_text_key_pressed)
        self.cmb_search_text.bind('<<ComboboxSelected>>', self.help_search_text_key_pressed)
        self.btn_search_prev = Button(self.frm_help_search, text="<", fg="black", state=NORMAL, command=self.help_search_previous)
        self.btn_search_prev.place(x=260, y=5, width=40, height=20)
        self.btn_search_next = Button(self.frm_help_search, text=">", fg="black", state=NORMAL, command=self.help_search_next)
        self.btn_search_next.place(x=310, y=5, width=40, height=20)
        self.btn_search_clear = Button(self.frm_help_search, text="Clear", fg="black", state=NORMAL, command=self.help_search_clear)
        self.btn_search_clear.place(x=360, y=5, width=80, height=20)
        self.lab_search_occur_nb = Label(self.frm_help_search, text="", fg="black", borderwidth=0, relief="solid", anchor=W)
        self.lab_search_occur_nb.place(x=450, y=5, width=100, height=20)
        # help text box
        self.frm_help_text = Frame(self.frm_help)
        self.frm_help_text.place(x=0, y=30, height=300, relwidth=1.0)
        scrollbarv = ttk.Scrollbar(self.frm_help_text, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        self.txt_help = Text(self.frm_help_text, fg="black", bg='azure', bd=3, wrap="word", font='Calibri 11', selectbackground="grey")
        self.txt_help.pack(side=BOTTOM, fill=BOTH, expand=True)
        self.txt_help.config(yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.txt_help.yview)
        # define the tags for the syntax highlighting
        self.txt_help.tag_config(self.tag_field, foreground='red3')
        self.txt_help.tag_config(self.tag_comment, foreground='chartreuse4')
        self.txt_help.tag_config(self.tag_obj_UID, foreground='blue2', font='Calibri 11 bold')
        self.txt_help.tag_config(self.tag_title, foreground='red3', font='Calibri 11 bold')

        # list to search in the GrandOrgue ODF and display the search results, with vertical scroll bar
        # a main frame is used to encapsulate two other frames, one for the search widgets, one for the list box and his vertical scroll bar
        self.frm_search = Frame(self.notebook)
        self.frm_search.pack(fill=BOTH, expand=True)
        # widgets to search a text
        self.frm_odf_search = Frame(self.frm_search)
        self.frm_odf_search.place(x=0, y=0, height=30, relwidth=1.0)
        self.ent_odf_search_text = Entry(self.frm_odf_search)
        self.ent_odf_search_text.place(x=20, y=5, width=170, height=20)
        self.btn_odf_search = Button(self.frm_odf_search, text="Search", fg="black", state=NORMAL, command=self.odf_do_search)
        self.btn_odf_search.place(x=200, y=5, width=80, height=20)
        # search results list box
        self.frm_odf_sresults = Frame(self.frm_search)
        self.frm_odf_sresults.place(x=0, y=30, height=300, relwidth=1.0)
        scrollbarv = ttk.Scrollbar(self.frm_odf_sresults, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        self.lst_odf_sresults = Listbox(self.frm_odf_sresults, bg='light yellow', font='Calibri 11', fg="black", exportselection=0, selectmode='single', activestyle='none')
        self.lst_odf_sresults.pack(side=LEFT, fill=BOTH, expand=True)
        self.lst_odf_sresults.bind('<Double-1>', self.odf_search_results_list_selected)
        self.lst_odf_sresults.config(yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.lst_odf_sresults.yview)

        # list to navigate inside the Hauptwerk objects in the ODF, with vertical scroll bar
        # a main frame is used to encapsulate two other frames, one for the search widgets, one for the list box and his vertical scroll bar
        self.frm_hw_browser = Frame(self.notebook)
        self.frm_hw_browser.pack(fill=BOTH, expand=True)
        # widgets to search an object UID
        self.frm_hw_uid_search = Frame(self.frm_hw_browser)
        self.frm_hw_uid_search.place(x=0, y=0, height=30, relwidth=1.0)
        self.ent_hw_uid_search_text = Entry(self.frm_hw_uid_search, text='HW UID to search')
        self.ent_hw_uid_search_text.place(x=20, y=5, width=170, height=20)
        self.btn_hw_uid_search = Button(self.frm_hw_uid_search, text="Search", fg="black", state=NORMAL, command=self.odf_do_search_hw)
        self.btn_hw_uid_search.place(x=200, y=5, width=80, height=20)
        # browser list box
        self.frm_hw_browser_list = Frame(self.frm_hw_browser)
        self.frm_hw_browser_list.place(x=0, y=30, height=300, relwidth=1.0)
        scrollbarv = ttk.Scrollbar(self.frm_hw_browser_list, orient='vertical')
        scrollbarv.pack(side=RIGHT, fill=Y)
        self.lst_hw_browser = Listbox(self.frm_hw_browser_list, bg='alice blue', font='Calibri 11', fg="black", exportselection=0, selectmode='single', activestyle='none')
        self.lst_hw_browser.pack(side=LEFT, fill=BOTH, expand=True)
        self.lst_hw_browser.bind('<<ListboxSelect>>', self.objects_list_selected_hw)
        self.lst_hw_browser.bind('<Double-1>', self.objects_list_do_update_hw)
        self.lst_hw_browser.config(yscrollcommand=scrollbarv.set)
        scrollbarv.config(command=self.lst_hw_browser.yview)

        # create the notebook tabs, and attach the frames to them
        self.notebook.add(self.frm_logs, text="    Logs    ")
        self.notebook.add(self.frm_help, text="    Help    ")
        self.notebook.add(self.frm_search, text="    Search in ODF    ")
        self.notebook.add(self.frm_hw_browser, text="    Hauptwerk objects    ")
        self.notebook.hide(self.frm_hw_browser)  # will be visible only if a Hauptwerk ODF is opened

        self.wnd_main.geometry('1600x800+50+50') # to trigger the call to wnd_main_configure to resize the widgets
        self.gui_status_do_update()

        # launch a timer to execute 200ms after the application init some time consuming activities
        self.wnd_main.after(200, self.do_boot_loadings)

        return self.wnd_main

    #-------------------------------------------------------------------------------------------------
    def wnd_main_configure(self, event):
        #--- (GUI event callback) the main window configuration has changed

        if str(event.widget) == '.':
            # configure event of the main window
            # resize some widgets so that they fit the size of the main window
            self.frm_object_list.place(height=int(event.height) - self.frm_object_list.winfo_y() - 10)
            self.frm_object_tree.place(height=int(event.height) - self.frm_object_tree.winfo_y() - 10)
            self.frm_object_text.place(height=int(event.height) - self.frm_object_text.winfo_y() - 10)
            self.notebook.place(width=int(event.width) - self.notebook.winfo_x() - 10, height=int(event.height) - self.notebook.winfo_y() - 10)
            self.frm_help_text.place(height=int(event.height) - self.frm_help_text.winfo_y() - 50)
            self.frm_odf_sresults.place(height=int(event.height) - self.frm_odf_sresults.winfo_y() - 50)
            self.frm_hw_browser_list.place(height=int(event.height) - self.frm_hw_browser_list.winfo_y() - 50)

    #-------------------------------------------------------------------------------------------------
    def wnd_main_quit(self):
        #--- (GUI event callback) the user has clicked on the button "Quit" or window top-right "X"

        if self.save_modif_before_change(True, True):
            # the user has saved his modifications if he wanted and has not canceled the operation
            self.wnd_main.destroy()

    #-------------------------------------------------------------------------------------------------
    def do_boot_loadings(self):
        #--- function to execute CPU time consuming loading operations just after the boot of the application
        #--- in order to not slowdown the application GUI appearance time

        # load an ODF (for debug only)
##        file_name_str = "D:/fichiers/Python/OdfEdit/ODF_examples/demo.organ"
##        file_name_str = "D:\\fichiers\\Python\\OdfEdit\\ODF_examples\\Giubiasco.organ"
##        file_name_str = "D:/GrandOrgue/SampleSet Demo/demo.organ"
##        if self.odf_data.odf_lines_load(file_name_str):
##            # the file has been loaded properly
##            # update the objects list and tree
##            self.selected_object_UID = ''
##            self.selected_object_type = ''
##            self.objects_list_tree_do_update()
##            self.gui_status_do_update()
##        self.events_log_text_display()

        # load the help text
        self.help_text_load()

        # load the Hauptwerk attributes dictionary
        self.odf_conv.HW_ODF_attr_dic_file_load()

        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def file_new(self):
        #--- (GUI event callback) the user has clicked on the button "New"
        #--- do a reset of the objects list/tree, edit box and ODF data

        if self.save_modif_before_change(file_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            self.selected_object_UID = ''
            self.selected_object_type = ''
            # clear the object text box
            self.object_text_do_update()
            # clear the objects list
            self.lst_objects_list.delete(0, END)
            self.lst_hw_browser.delete(0, END)
            # clear the objects tree
            for item in self.trv_objects_tree.get_children():
                self.trv_objects_tree.delete(item)
            # clear the ODF data
            self.odf_data.odf_reset_all_data()

            self.data_changed = False
            # update the status of some GUI widgets
            self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def file_open(self):
        #--- (GUI event callback) the user has clicked on the button "Open"

        if self.save_modif_before_change(file_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            # let the user select the ODF file to open
            file_name_str = fd.askopenfilename(title='Open an Organ Definition File (ODF)', filetypes=[('All supported ODF', '*.organ *.Organ_Hauptwerk_xml'), ('GrandOrgue ODF', '*.organ'), ('Hauptwerk ODF', '*.Organ_Hauptwerk_xml')])
            if file_name_str != '':
                # a file has been selected by the user
                filename_str, file_extension_str = os.path.splitext(file_name_str)

                # select the logs tab of the notebook to show the opening logs
                self.notebook.select(self.frm_logs)

                # reset the data and HMI
                self.file_new()
                self.notebook.hide(self.frm_hw_browser)

                if file_extension_str == '.Organ_Hauptwerk_xml':
                    # Hauptwerk ODF selected : build a GrandOrgue ODF which uses the Hauptwerk sample set

                    HW_ODF_file_name_str = file_name_str
                    file_name_str = ''
                    # define the name of the built GO ODF according to the name of the HW ODF : same path and file name, only the extension is changed
                    GO_ODF_file_name = HW_ODF_file_name_str.replace('.Organ_Hauptwerk_xml', '.organ')

                    # legal message displayed to the user before to start the ODF building
                    confirm = messagebox.askokcancel(title="Hauptwerk ODF conversion to GrandOrgue format", message=HW_CONV_MSG)
                    #confirm = True
                    if confirm:  # answer is yes
                        if self.odf_conv.GO_ODF_build_from_HW_ODF(HW_ODF_file_name_str, GO_ODF_file_name, self.progress_status_update):
                            # the GO ODF building has succeeded
                            if DISP_HW_OBJECTS_TREE:
                                # display the HW objects notebook tab and list inside this tab
                                self.notebook.add(self.frm_hw_browser)
                                self.objects_list_do_update_hw()
                            # the built GO ODF will be then loaded
                            file_name_str = GO_ODF_file_name
                        else:
                            self.odf_conv.events_log_add('ERROR : something went wrong while converting the Hauptwerk ODF in a GrandOrgue ODF')
                        self.events_log_text_display()

                if file_name_str != '':
                    # GrandOrgue ODF selected or built from a Hauptwerk ODF
                    if self.odf_data.odf_lines_load(file_name_str):
                        # the file has been loaded properly
                        # update the objects list / tree / text
                        self.initial_dir = file_name_str
                        self.selected_object_UID = ''
                        self.selected_object_type = ''
                        self.objects_list_do_update()
                        self.objects_tree_do_update()
                        self.object_text_do_update()

                        self.data_changed = False

                self.gui_status_do_update()
                self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def file_save(self):
        #---  (GUI event callback) the user has clicked on the button "Save"

        if self.odf_data.odf_file_name == '':
            # no file name known, do a 'save as' operation
            self.file_saveas()
        elif self.odf_data.odf_lines_save(''):
            # the ODF data have been correctly saved in the loaded ODF file
            self.data_changed = False
            self.gui_status_do_update()
        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def file_saveas(self):
        #---  (GUI event callback) the user has clicked on the button "Save as"

        # let the user select the ODF file to which make the save
        file_name_str = fd.asksaveasfilename(title='Save in ODF...', filetypes=[('ODF', '*.organ')])

        if file_name_str != '':
            # a file has been selected by the user
            if self.odf_data.odf_lines_save(file_name_str):
                # the ODF data have been correctly saved
                self.data_changed = False
                self.gui_status_do_update()
            self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def save_modif_before_change(self, file_change=False, object_change=False):
        #--- before a file change (file_change=True) or a selected object change (object_change=True) or a window closing
        #--- ask to the user if he wants to save his modifications if any, if the answer is yes then do it
        #--- return True if the user has not answered Cancel

        operation_not_canceled = True

        if (file_change or object_change) and self.object_edited:
            # the coming change is at file or object level and an object content has been edited
            # ask to the user if he wants to apply the changed object data
            confirm = messagebox.askyesnocancel(title="Data changed", message="Do you want to apply the changed object data ?")
            if confirm:  # answer is yes
                self.object_text_apply_chg()
            elif confirm is None:  # answer is cancel
                operation_not_canceled = False
            else:  # answer is no
                pass

        if file_change and self.data_changed and operation_not_canceled:
            # the coming change is at file level and the ODF data have been changed (and the operation has not been yet canceled just before)
            # ask to the user if he wants to save the changed ODF data
            confirm = messagebox.askyesnocancel(title="Data changed", message="Do you want to save the modified ODF data ?")
            if confirm:  # answer is yes
                self.file_save()
            elif confirm is None:  # answer is cancel
                operation_not_canceled = False
            else:  # answer is no
                pass

        return operation_not_canceled

    #-------------------------------------------------------------------------------------------------
    def gui_events_block(self):
        #--- set the flag which blocks the GUI events processing
        #--- returns True if the events are already blocked, else False (in case of False the caller can process its GUI event)
        #--- this permits to avoid the application to react to all the GUI events caused by changes that ifself is making in widgets
        #--- which causes several bad side effects in the widgets behavior and final status

        if self.gui_events_blocked == False:
            # the events are not yet blocked
            self.gui_events_blocked = True
            # launch a timer which will unblock the events 200ms later
            self.wnd_main.after(200, self.gui_events_unblock)
            return False
        else:
            return True

    #-------------------------------------------------------------------------------------------------
    def gui_events_unblock(self):
        #--- (GUI event callback) end of a timer started by the function gui_events_block
        #--- reset the flag which blocks the GUI events processing

        self.gui_events_blocked = False

    #-------------------------------------------------------------------------------------------------
    def gui_status_do_update(self):
        #--- update the status of some GUI widgets in a single time, according to some status of the application

##        print('\ngui_status_do_update, selected object is ' + self.selected_object_UID)
##        print('   call stack : ' + inspect.stack()[1].function + ' / ' + inspect.stack()[2].function + ' / ' + inspect.stack()[3].function)

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        objects_nb = len(self.odf_data.odf_objects_dic)

        # button "Save"
        self.btn_odf_file_save['state'] = NORMAL if (self.odf_data.odf_file_name != '' and self.data_changed) else DISABLED
        self.btn_odf_file_save['foreground'] = 'red' if (self.odf_data.odf_file_name != '' and self.data_changed) else 'grey'

        # button "Save as"
        self.btn_odf_file_saveas['state'] = NORMAL if objects_nb > 0 else DISABLED

        # button "Apply changes"
        self.btn_object_apply_chg['state'] = NORMAL if self.object_edited and self.selected_object_type == 'GO' else DISABLED
        self.btn_object_apply_chg['foreground'] = 'red' if self.object_edited and self.selected_object_type == 'GO' else 'grey'

        # button "Delete"
        self.btn_object_delete['state'] = NORMAL if (self.selected_object_UID != '' and self.selected_object_UID != 'Header' and self.selected_object_type == 'GO') else DISABLED

        # button "Do check"
        self.btn_data_check['state'] = NORMAL if objects_nb > 0 else DISABLED

        # button "Show help"
        self.btn_show_help['state'] = NORMAL if self.selected_object_UID != '' else DISABLED

        # buttons "Collapse all" and "Expand all"
        self.btn_collapse_all['state'] = NORMAL if objects_nb > 0 else DISABLED
        self.btn_expand_all['state'] = NORMAL if objects_nb > 0 else DISABLED

        # buttons to search previous or next or clear the search in the help
        is_search_text = (self.cmb_search_text.get() != '')
        self.btn_search_prev['state'] = NORMAL if is_search_text else DISABLED
        self.btn_search_next['state'] = NORMAL if is_search_text else DISABLED
        self.btn_search_clear['state'] = NORMAL if is_search_text else DISABLED

        # label with the loaded ODF name
        if self.odf_data.odf_file_name == '':
            if objects_nb == 0:
                self.lab_odf_file_name.config(text='Click on the button "Open" to load a GrandOrgue or Hauptwerk ODF')
            else:
                self.lab_odf_file_name.config(text='Click on the button "Save as" to define a file name')
        else:
            self.lab_odf_file_name.config(text=self.odf_data.odf_file_name)

        # label with the number of objects
        if objects_nb == 0:
            self.lab_objects_nb.config(text="None object")
        elif objects_nb == 1:
            self.lab_objects_nb.config(text="1 object")
        else:
            self.lab_objects_nb.config(text=str(objects_nb) + " objects")

        if objects_nb > 0:
            # objects list : select the item corresponding to the selected object ID
            self.lst_objects_list.selection_clear(0, 'end')
            for i in range(0, self.lst_objects_list.size()):
                if self.lst_objects_list.get(i).split(' ')[0] == self.selected_object_UID:
                    self.lst_objects_list.selection_set(i)
                    self.lst_objects_list.see(i)
                    break;

            # objects tree : select the items corresponding to the selected object ID
            # unselect the root of the objects tree if it was selected
            self.trv_objects_tree.selection_remove('0')
            for iid in self.trv_objects_tree.get_children('0'):
                self.__objects_tree_select_nodes(iid, self.selected_object_UID)

            # HW objects list : select the item corresponding to the selected object ID
            self.lst_hw_browser.selection_clear(0, 'end')
            for i in range(0, self.lst_hw_browser.size()):
                if self.lst_hw_browser.get(i).split(' (')[0].strip() == self.selected_object_UID:
                    self.lst_hw_browser.selection_set(i)
                    self.lst_hw_browser.see(i)
                    break;

    #-------------------------------------------------------------------------------------------------
    def objects_list_selected(self, event):
        #--- (GUI event callback) the user has selected an item in the objects list widget
        #--- select the same object ID in the objects list widget, and show the object ID content in the object text box

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        # get the selected indice
        selected_indice = self.lst_objects_list.curselection()

        if self.save_modif_before_change(object_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            if selected_indice != ():
                # an item of the objects list widget is selected
                # recover in the objects list widget the object ID of the selected item (before the opening parenthesis)
                self.selected_object_UID = self.lst_objects_list.get(selected_indice[0]).split(' (')[0]
                self.selected_object_type = 'GO'

                # update the object text box
                self.object_text_do_update()
                # update the status of GUI widgets
                self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def objects_list_selected_hw(self, event):
        #--- (GUI event callback) the user has selected an item in the Hauptwerk objects list widget

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        # get the selected indice in the list
        selected_indice = self.lst_hw_browser.curselection()

        if selected_indice != ():
            # recover the corresponding object ID
            self.selected_object_UID = self.lst_hw_browser.get(selected_indice[0]).split(' (')[0].strip()
            if self.selected_object_UID[0] == '*':
                self.selected_object_UID = ''
            self.selected_object_type = 'HW'

            # update the object text box
            self.object_text_do_update()
            # update the status of GUI widgets
            self.gui_status_do_update()

            if self.selected_object_UID[:-6] == 'Switch':
                HW_switch_dic = self.odf_conv.HW_ODF_get_object_dic(self.selected_object_UID)
                obj_uid_str = ''
                HW_switch_data_dic = {}
                self.odf_conv.HW_ODF_get_controlled_switches(HW_switch_dic, 'Stop', HW_switch_data_dic)
                if len(HW_switch_data_dic['controlled_switches']) > 0:
                    for HW_object_dic in HW_switch_data_dic['controlled_switches']:
                        obj_uid_str += f"Controlled STOP : {HW_object_dic['_HW_uid']} ({HW_object_dic['Name']}) / "

                HW_switch_data_dic = {}
                self.odf_conv.HW_ODF_get_controlled_switches(HW_switch_dic, 'StopRank', HW_switch_data_dic)
                if len(HW_switch_data_dic['controlled_switches']) > 0:
                    for HW_object_dic in HW_switch_data_dic['controlled_switches']:
                        obj_uid_str += f"Controlled STOP RANK : {HW_object_dic['_HW_uid']} ({HW_object_dic['Name']}) / "

                HW_switch_data_dic = {}
                self.odf_conv.HW_ODF_get_controlled_switches(HW_switch_dic, 'KeyAction', HW_switch_data_dic)
                if len(HW_switch_data_dic['controlled_switches']) > 0:
                    for HW_object_dic in HW_switch_data_dic['controlled_switches']:
                        obj_uid_str += f"Controlled KEY ACTION : {HW_object_dic['_HW_uid']} ({HW_object_dic['Name']}) / "

                self.odf_conv.HW_ODF_get_controlled_switches(HW_switch_dic, '', HW_switch_data_dic)

                obj_uid_str += f"Code {HW_switch_data_dic['switch_asgn_code']}"

##                print(obj_uid_str)


    #-------------------------------------------------------------------------------------------------
    def objects_list_do_update(self):
        #--- do an update the objects list widget

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # update the objects list widgets
        self.lst_objects_list.delete(0, END)
        for dict_key, dict_value in self.odf_data.odf_objects_dic.items():
            self.lst_objects_list.insert(END, dict_key + " (" + dict_value[IDX_OBJ_NAME] + ")")

    #-------------------------------------------------------------------------------------------------
    def objects_list_do_update_hw(self, event=0):
        #--- (GUI event callback and normal function) do an update the Hauptwerk objects list widget

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # update the HW objects list widgets
        if len(self.odf_conv.HW_ODF_dic):
            # there are HW ODF data in the dictionary
            if self.selected_object_UID != '' and self.selected_object_UID[0] == '*': return

            root_object_id = "_General"

            if self.selected_object_UID == '' or self.selected_object_type != 'HW':
                center_object_UID = root_object_id
            else:
                center_object_UID = self.selected_object_UID

            selected_object_dic = self.odf_conv.HW_ODF_get_object_dic(center_object_UID)
            if selected_object_dic != None:
                # delete all the elements of the list
                self.lst_hw_browser.delete(0, END)
                self.lst_hw_browser.insert(END, '*** OBJECTS RELATIONSHIP (parents/current in red/children) ***')

                # display the parents of the selected object
                objects_uid_list = []
                for object_dic in selected_object_dic['_parents']:
                    objects_uid_list.append(object_dic['_HW_uid'])
                for object_uid_str in sorted(objects_uid_list):
                    object_dic = self.odf_conv.HW_ODF_get_object_dic(object_uid_str)
                    obj_name = self.odf_conv.HW_ODF_get_attribute_value(object_dic, 'Text')
                    if obj_name == None: obj_name = self.odf_conv.HW_ODF_get_attribute_value(object_dic, 'Name')
                    if obj_name == None: obj_name = ''
                    obj_name = object_uid_str + ' (' + obj_name + ')'
                    self.lst_hw_browser.insert(END, ' ' + obj_name)

                # display the selected object
                obj_name = self.odf_conv.HW_ODF_get_attribute_value(selected_object_dic, 'Text')
                if obj_name == None: obj_name = self.odf_conv.HW_ODF_get_attribute_value(selected_object_dic, 'Name')
                if obj_name == None: obj_name = ''
                obj_name = center_object_UID + ' (' + obj_name + ')'
                self.lst_hw_browser.insert(END, '       ' + obj_name)
                self.lst_hw_browser.itemconfig(END, foreground='red')

                # display the children of the selected object
                objects_uid_list = []
                for object_dic in selected_object_dic['_children']:
                    objects_uid_list.append(object_dic['_HW_uid'])
                for object_uid_str in sorted(objects_uid_list):
                    object_dic = self.odf_conv.HW_ODF_get_object_dic(object_uid_str)
                    obj_name = self.odf_conv.HW_ODF_get_attribute_value(object_dic, 'Text')
                    if obj_name == None: obj_name = self.odf_conv.HW_ODF_get_attribute_value(object_dic, 'Name')
                    if obj_name == None: obj_name = ''
                    obj_name = object_uid_str + ' (' + obj_name + ')'
                    if len(self.odf_conv.HW_ODF_get_attribute_value(object_dic, '_children')) > 0:
                        obj_name += '  >>>'
                    self.lst_hw_browser.insert(END, '               ' + obj_name)

            self.lst_hw_browser.insert(END, '*** OBJECTS WITH NO PARENT (>>> means has children) ***')
            self.lst_hw_browser.insert(END, ' _General () >>>')

            # add at the end all the objects which have no parent except some types
            objects_uid_list = []
            for HW_object_type_str, HW_object_type_dic in self.odf_conv.HW_ODF_dic.items():
                # parse the HW object types
                if not HW_object_type_str.startswith(('Pi', 'Sa', 'TremulantWaveformP', 'SwitchL', '_General')):
                    # excluded objects types are : Pipe_xxx, Sample, TremulantWaveformPipe, SwitchLinkage, _General
                    # the current HW object type can be added in the list
                    for object_dic in HW_object_type_dic.values():
                        # parse the HW objects of the current HW objects type
                        if len(object_dic['_parents']) == 0:
                            # the current object has no parent
                            objects_uid_list.append(object_dic['_HW_uid'])

            for object_uid_str in sorted(objects_uid_list):
                object_dic = self.odf_conv.HW_ODF_get_object_dic(object_uid_str)
                obj_name = self.odf_conv.HW_ODF_get_attribute_value(object_dic, 'Name')
                if obj_name == None: obj_name = ''
                obj_name = object_dic['_HW_uid'] + ' (' + obj_name + ')'
                if len(self.odf_conv.HW_ODF_get_attribute_value(object_dic, '_children')) > 0:
                    obj_name = obj_name + ' >>>'
                self.lst_hw_browser.insert(END, ' ' + obj_name)

        self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def objects_tree_selected(self, event):
        #--- (GUI event callback) the user has selected an item in the objects tree widget
        #--- select the same object ID in the objects tree widget, and show the object ID content in the object text box

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        # get the indice of the selected item
        selected_indice = self.trv_objects_tree.focus()

        if self.save_modif_before_change(object_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            # recover the object ID
            self.selected_object_UID = self.trv_objects_tree.item(selected_indice, option='text').split(' (')[0]
            self.selected_object_type = 'GO'

            # update the object text box
            self.object_text_do_update()
            # update the status of GUI widgets
            self.gui_status_do_update()

            # make the selected item visibile if it is no more visible after the execution of gui_status_do_update due to some upper nodes opening
            if self.trv_objects_tree.bbox(selected_indice) == '':
                self.trv_objects_tree.see(selected_indice)

    #-------------------------------------------------------------------------------------------------
    def objects_tree_do_update(self):
        #--- do an update of the objects tree widgets

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # update the objects tree widget
        # delete all the nodes of the tree
        for item in self.trv_objects_tree.get_children():
            self.trv_objects_tree.delete(item)
        if len(self.odf_data.odf_objects_dic):
            # add the root node
            self.node_id = 0
            root_object_id = "Header"
            parent_node_id = str(self.node_id)
            self.trv_objects_tree.insert('', 0, str(self.node_id), text=root_object_id, open=True)
            # add in the tree the children of the objects which have no parent (i.e. which the parent is the Root)
            # inside the called function all the children will be added recursively
            for dict_key, dict_value in self.odf_data.odf_objects_dic.items():
                if len(dict_value[IDX_OBJ_PAR]) == 0:
                    # the object has no parents
                    self.__objects_tree_add_child(parent_node_id, dict_key)

    #-------------------------------------------------------------------------------------------------
    def objects_tree_expand_all(self):
        #--- (GUI event callback) the user has pressed the button "Expand all"
        # expend all the nodes of the objects tree widget

        self.trv_objects_tree.item('0', open=True)
        for iid in self.trv_objects_tree.get_children('0'):
            self.__objects_tree_open_node_and_children(iid, True)

    #-------------------------------------------------------------------------------------------------
    def objects_tree_collapse_all(self):
        #--- (GUI event callback) the user has pressed the button "Collapse all"
        # collapse all the nodes of the objects tree widget except the root and the 'Organ' nodes

        self.trv_objects_tree.item('0', open=True)
        for iid in self.trv_objects_tree.get_children('0'):
            self.__objects_tree_open_node_and_children(iid, False)

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_open_node_and_children(self, node_iid, open_status):
        #--- recursive function to open (if True, else close) the given node and his children in the objects tree

        if self.trv_objects_tree.item(node_iid, option='text') == 'Organ':
            # the Organ node must stay always opened
            self.trv_objects_tree.item(node_iid, open=True)
        else:
            self.trv_objects_tree.item(node_iid, open=open_status)

        # apply the open status to the children nodes
        for iid in self.trv_objects_tree.get_children(node_iid):
            self.__objects_tree_open_node_and_children(iid, open_status)

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_open_node_and_parents(self, node_iid):
        #--- recursive function to open the given node and his parents in the objects tree

        if node_iid != '0':
            self.trv_objects_tree.item(node_iid, open=True)

            # apply the open status to the children nodes
            self.__objects_tree_open_node_and_parents(self.trv_objects_tree.parent(node_iid))

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_select_nodes(self, node_iid, object_UID):
        #--- recursive function to select the nodes of the objects tree which contain the given object ID

        if self.trv_objects_tree.item(node_iid)['text'].split(' (')[0] == object_UID:
            # the node node_iid corresponds to the object ID : select it
            self.trv_objects_tree.selection_add(node_iid)
            # open the parents of the node
            self.__objects_tree_open_node_and_parents(self.trv_objects_tree.parent(node_iid))
        else:
            self.trv_objects_tree.selection_remove(node_iid)

        # do the operation for the children of node_iid
        for iid in self.trv_objects_tree.get_children(node_iid):
            self.__objects_tree_select_nodes(iid, object_UID)

    #-------------------------------------------------------------------------------------------------
    def __objects_tree_add_child(self, parent_node_id, child_object_UID):
        #--- recursive function to add in the objects tree widget the given child linked to the given parent

        # add in the tree a node for the given child under the given parent
        self.node_id += 1
        # recover the name of the object ID in the dictionnary
        obj_name = self.odf_data.odf_objects_dic.get(child_object_UID)[IDX_OBJ_NAME]
        if child_object_UID == "Organ":
            # for the Organ object, open the tree node in addition to add the child
            self.trv_objects_tree.insert(parent_node_id, 'end', str(self.node_id), text=child_object_UID, open=True)
        else:
            self.trv_objects_tree.insert(parent_node_id, 'end', str(self.node_id), text=child_object_UID + ' (' + obj_name + ')')
        if child_object_UID == self.selected_object_UID:
            # the added object ID corresponds to the selected object ID, then select it and show it
            self.trv_objects_tree.selection_add(str(self.node_id))
            self.trv_objects_tree.see(str(self.node_id))

        # the child becomes the parent for the next recursive call
        new_parent_node_id = str(self.node_id)
        new_parent_UID = child_object_UID

        # parse the children of new parent to add the corresponding children nodes
        if new_parent_UID in self.odf_data.odf_objects_dic:
            # the new parent object ID is actually present in the dictionnary
            children_list = self.odf_data.odf_objects_dic[new_parent_UID][IDX_OBJ_CHI]
            if len(children_list) > 0:
                for child_UID in children_list:
                    self.__objects_tree_add_child(new_parent_node_id, child_UID)
        else:
            pass  # do nothing if the object ID is not found in the dictionnary

##    #-------------------------------------------------------------------------------------------------
##    def __objects_tree_add_child_hw(self, parent_node_id, child_object_id):
##        #--- recursive function to add in the Hauptwerk objects tree widget the given child linked to the given parent
##
##        self.node_depth += 1
##
##        # add in the tree a node for the given child under the given parent
##        self.node_id += 1
##        # recover the name of the object ID in the dictionnary
##        (child_obj_type, child_obj_idx_in_type) = self.odf_conv.HW_ODF_split_object_uid(child_object_id)
##        obj_name = self.odf_conv.HW_ODF_get_attribute_value(child_obj_type, child_obj_idx_in_type, 'Name')
##        obj_children_list = self.odf_conv.HW_ODF_get_attribute_value(child_obj_type, child_obj_idx_in_type, '_children')
##        # add the child object in the children of the parent node
##        obj_name = child_object_id + ' (' + obj_name + ')'
##
##        if len(obj_children_list) > 0:
##            obj_name = obj_name + ' >>>'
##        self.trv_hw_objects_tree.insert(parent_node_id, 'end', str(self.node_id), text=obj_name)
##
##        # the child becomes the parent for the next recursive call
##        new_parent_node_id = str(self.node_id)
##
##        # check if the new parent text is already present in its parents (if yes exit the function, to avoid circle references in children observed with the SwitchLinkage)
####        par_node_id = self.trv_hw_objects_tree.parent(new_parent_node_id)
####        while par_node_id != '0':
####            if self.trv_hw_objects_tree.item(par_node_id, 'text') == obj_name:
####                return
####            par_node_id = self.trv_hw_objects_tree.parent(par_node_id)
##
##        # parse the children of new parent to add the corresponding children nodes
##        children_list = self.odf_conv.HW_ODF_get_attribute_value(child_obj_type, child_obj_idx_in_type, '_children')
##        if children_list != '':
##            children_list.sort()
##            for child_id in children_list:
##                if self.node_depth <= 3:
##                    self.__objects_tree_add_child_hw(new_parent_node_id, child_id)
##
##        self.node_depth -= 1

    #-------------------------------------------------------------------------------------------------
    def object_text_do_update(self):
        # -- update the content of the object text box widget

        object_data_list = []
        if self.selected_object_UID != '':
            if self.selected_object_type == 'GO':
                # get the list of the selected GrandOrgue object ID data
                object_data_list = self.odf_data.object_get_data_list(self.selected_object_UID)
            elif self.selected_object_type == 'HW':
                # get the list of the selected GrandOrgue object ID data
                object_data_list = self.odf_conv.HW_ODF_get_object_data_list(self.selected_object_UID)

        # write the object data in the object text box
        self.txt_object_text.delete(1.0, "end")
        self.txt_object_text.insert(1.0, '\n'.join(object_data_list))

        # update object the parents list label
        self.object_text_do_parents_update()

        # highlight the syntax of the object data
        self.odf_syntax_highlight(self.txt_object_text)

        # reset the text modified flag
        self.txt_object_text.edit_modified(False)
        self.object_edited = False

    #-------------------------------------------------------------------------------------------------
    def object_text_do_parents_update(self):
        #--- update the parents list label

        self.lab_parents_list['foreground'] = 'black'
        if self.selected_object_UID in ('', 'Header') or self.selected_object_type == 'HW':
            # no object ID selected or header selected : none parent to display
            self.lab_parents_list.config(text='')
        else:
            try:
                # recover the number of parents for the selected object ID
                nb_parents = len(self.odf_data.odf_objects_dic[self.selected_object_UID][IDX_OBJ_PAR])
            except:
                # object not found in the dictionnary
                self.lab_parents_list.config(text="Undefined object")
            else:
                if nb_parents == 0:
                    self.lab_parents_list.config(text="")
                elif nb_parents == 1:
                    self.lab_parents_list.config(text=f"{self.selected_object_UID} has 1 parent object : {' '.join(self.odf_data.odf_objects_dic[self.selected_object_UID][IDX_OBJ_PAR])}")
                elif nb_parents >= 1:
                    self.lab_parents_list.config(text=f"{self.selected_object_UID} has {nb_parents} parent objects : {' '.join(self.odf_data.odf_objects_dic[self.selected_object_UID][IDX_OBJ_PAR])}")

    #-------------------------------------------------------------------------------------------------
    def object_text_changed(self, event):
        #--- (GUI event callback) the user has made a change in the object text box

        # exit this function if the GUI events have to be ignored
        if self.gui_events_block(): return

        if self.txt_object_text.edit_modified() and self.object_edited == False:
            # update the status of GUI widgets
            self.object_edited = True
            self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def object_text_apply_chg(self):
        #--- (GUI event callback) the user has clicked on the button "Apply changes"
        #--- apply the content of the object text widget in the ODF data

        # convert the object text lines in list elements
        object_list = self.txt_object_text.get(1.0, "end").splitlines()

        # apply the object data in the ODF data
        ret = self.odf_data.object_set_data_list(self.selected_object_UID, object_list)
        if ret != '':
            # the modification has been applied
            self.data_changed = True
            # recover the object ID of the applied text
            self.selected_object_UID = ret
            self.selected_object_type = 'GO'
            # update the objects list and tree
            self.objects_list_do_update()
            self.objects_tree_do_update()
            # update object the parents list label
            self.object_text_do_parents_update()

            # reset the edit modified flag
            self.txt_object_text.edit_modified(False)
            self.object_edited = False

            # update the status of GUI widgets
            self.gui_status_do_update()

        # update the events log text
        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def object_text_delete(self):
        #--- (GUI event callback) the user has clicked on the button "Delete" to delete the current selected object ID

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # remove the object in the ODF data
        if self.odf_data.object_remove(self.selected_object_UID):
            # the object has been removed
            # clear the current object ID
            self.selected_object_UID = ''
            self.selected_object_type = ''
            # update the objects list and tree
            self.objects_list_do_update()
            self.objects_tree_do_update()
            # update the object text
            self.object_text_do_update()

            # update the status of GUI widgets
            self.data_changed = True
            self.gui_status_do_update()

        # update the events log text
        self.events_log_text_display()

    #-------------------------------------------------------------------------------------------------
    def object_text_context_menu(self, event):
        #--- (GUI event callback) the user has made a right click in the object text box : open the context menu

        try:
            self.obj_txt_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.obj_txt_menu.grab_release()

    #-------------------------------------------------------------------------------------------------
    def object_text_clear(self):
        #--- (GUI event callback) the user has selected 'Clear all' in the context menu of the object text box

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # clear the current object ID
        self.selected_object_UID = ''
        self.selected_object_type = ''

        # update the object text
        self.object_text_do_update()

        # reset the edit modified flag
        self.txt_object_text.edit_modified(False)
        self.object_edited = False
        self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def object_text_key_pressed(self, event):
        #--- (GUI event callback) the user has pressed a keyboard key in the object text box

        # update the syntax highlighting
        self.odf_syntax_highlight(self.txt_object_text)

    #-------------------------------------------------------------------------------------------------
    def odf_do_search(self):
        #--- (GUI event callback) the user has clicked on the button search of the ODF search results tab

        # recover the text to search
        search_text = self.ent_odf_search_text.get()

        if search_text != '':
            object_UID = 'Header'
            results_list = []
            for line in self.odf_data.odf_lines_list:

                if self.odf_data.is_line_with_object_UID(line): # line with an object ID
                    object_UID = line[1:-1] # remove the brackets in first and last characters to get the object ID

                if search_text in line:
                    results_list.append(f'{object_UID} : {line}')

            results_list.sort()

            self.lst_odf_sresults.delete(0, END)
            self.lst_odf_sresults.insert(END, *results_list)

    #-------------------------------------------------------------------------------------------------
    def odf_do_search_hw(self):
        #--- (GUI event callback) the user has clicked on the button search of the HW ODF browser

        # recover the text to search (must be a HW object UID only)
        search_text = self.ent_hw_uid_search_text.get()

        if search_text != '':
            object_dic = self.odf_conv.HW_ODF_get_object_dic(search_text)
            if object_dic != None:
                self.selected_object_UID = search_text
                self.selected_object_type = 'HW'

                # update the HW objects list
                self.objects_list_do_update_hw()
                # update the object text box
                self.object_text_do_update()
                # update the status of GUI widgets
                self.gui_status_do_update()
            else:
                messagebox.showerror(title="Error", message=f'"{search_text}" is not a known HW UID')

    #-------------------------------------------------------------------------------------------------
    def odf_search_results_list_selected(self, event):
        #--- (GUI event callback) the user has clicked on an item of the ODF search results list

        # get the selected indice
        selected_indice = self.lst_odf_sresults.curselection()

        if self.save_modif_before_change(object_change=True):
            # the user has saved his modifications if he wanted and has not canceled the operation

            self.selected_object_UID = self.lst_odf_sresults.get(selected_indice[0]).split(' :')[0]
            self.selected_object_type = 'GO'

            # update the object text box
            self.object_text_do_update()
            # update the status of GUI widgets
            self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def events_log_text_context_menu(self, event):
        #--- (GUI event callback) the user has made a right click in the logs text box : open the context menu

        try:
            self.logs_txt_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.logs_txt_menu.grab_release()

    #-------------------------------------------------------------------------------------------------
    def events_log_text_display(self):
        #--- add in the events log text box widget the content of the events log buffer then clear it

        if len(self.odf_data.events_log_list) > 0:
            self.txt_events_log.insert('end', '\n' + '\n'.join(self.odf_data.events_log_list) + '\n')
        if len(self.odf_conv.events_log_list) > 0:
            self.txt_events_log.insert('end', '\n' + '\n'.join(self.odf_conv.events_log_list) + '\n')
        self.txt_events_log.see('end-1c linestart')  # to see the start of the last line of the text
        self.txt_events_log.update_idletasks() # to force a refresh of the text box

        # reset the events log buffer
        self.odf_data.events_log_clear()
        self.odf_conv.events_log_clear()

    #-------------------------------------------------------------------------------------------------
    def events_log_text_clear(self):
        #--- (GUI event callback) the user has selected 'Clear all' in the context menu of the logs text box

        # clear the content of the logs text box
        self.txt_events_log.delete(1.0, "end")

        # reset the events log buffer
        self.odf_data.events_log_clear()
        self.odf_conv.events_log_clear()

    #-------------------------------------------------------------------------------------------------
    def help_text_load(self):
        #--- load in the help text box widget the help for the user
        #--- done one time at the application start

        file_name_str = os.path.dirname(__file__) + '/Help.txt'

        try:
            with open(file_name_str, 'r') as f:
                # copy in the widget the help text
                self.txt_help.insert(1.0, f.read())
                # apply the ODF syntax highlighting
                self.odf_syntax_highlight(self.txt_help)
                # disable the text box to not permit its editing
                self.txt_help.configure(state='disabled')
                return True
        except OSError as err:
            # it has not be possible to open the file
            messagebox.showinfo(title="ERROR", message=f'Cannot open the file "{file_name_str}"\n{err}')
        except:
            # other error
            messagebox.showinfo(title="ERROR", message=f'Error while opening the file "{file_name_str}"\n{err}')

        return False

##        # copy in the widget the help text
##        self.txt_help.insert(1.0, HELP_TEXT)
##        # apply the ODF syntax highlighting
##        self.odf_syntax_highlight(self.txt_help)
##        # disable the text box to not permit its editing
##        self.txt_help.configure(state='disabled')

    #-------------------------------------------------------------------------------------------------
    def help_selected_object(self):
        #--- (GUI event callback) the user has clicked on the button "Show in help"
        #--- search and display in the help the part mentioning the selected object help

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        if self.selected_object_UID not in ["", "Header"]:
            #substitute the digits by the char 9 in the object ID to create a generic object ID
            gen_object_UID = '['
            for c in self.selected_object_UID: gen_object_UID += '9' if c.isdigit() else c
            gen_object_UID += ']'

            # put the generic object ID in the search text widget
            self.cmb_search_text.delete(0, END)
            self.cmb_search_text.insert(0, gen_object_UID)

            # update the status of some GUI widgets
            self.gui_status_do_update()

            # search the first occurence of the generic object ID
            self.help_search_next()

            # select the Help tab of the notebook
            self.notebook.select(self.frm_help)

    #-------------------------------------------------------------------------------------------------
    def help_search_next(self):
        #--- (GUI event callback) the user has clicked on the button '>'
        #--- show the next occurence of the text to search

        self.help_search_text(self.cmb_search_text.get(), True)

    #-------------------------------------------------------------------------------------------------
    def help_search_previous(self):
        #--- (GUI event callback) the user has clicked on the button '<'
        #--- show the previous occurence of the text to search

        self.help_search_text(self.cmb_search_text.get(), False)

    #-------------------------------------------------------------------------------------------------
    def help_search_clear(self):
        #--- (GUI event callback) the user has clicked on the button 'Clear'
        #--- clear the text to search (text box and highlighting)

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        self.cmb_search_text.delete(0, END)
        self.help_search_text('', False)
        self.lab_search_occur_nb.config(text='')

        # update the status of some GUI widgets
        self.gui_status_do_update()

    #-------------------------------------------------------------------------------------------------
    def help_search_text(self, text_to_find, search_next = True):
        # show in the help the next occurence (or previous if search_next=False) of the given text to find
        # highlight in yellow all the occurences of this text

        text_len = len(text_to_find)

        if self.text_in_search != text_to_find:
            # a new text has to be searched, highlight all its occurences in the entire help text

            # remove the highlight of the previous searched text occurences
            self.txt_help.tag_remove(self.tag_found, '1.0', END)
            nb_occurences = 0

            # store the new text to search
            self.text_in_search = text_to_find

            if text_to_find != '':
                # highlight the occurences of the text to find in the entire help
                self.txt_help.tag_config(self.tag_found, foreground='black', background='yellow', font='Calibri 11')
                # get the lines of the text widget
                lines = self.txt_help.get('1.0', END).splitlines()
                # parse all the lines
                for l in range(0, len(lines)):
                    idx = 0
                    while idx != -1:
                        # check the various occurences of the searched text in the current line (if any)
                        idx = lines[l].find(text_to_find, idx)
                        if idx != -1:
                            # highlight the found occurence in the line
                            self.txt_help.tag_add(self.tag_found, f'{l+1}.{idx}', f'{l+1}.{idx} + {text_len} chars')
                            # move the search index after the found occurence
                            idx += text_len
                            nb_occurences += 1

                # display the number of occurences of the searched text
                self.lab_search_occur_nb.config(text=f'{nb_occurences} occurences')

        if self.text_in_search != '':
            # search for the text in the widget
            if search_next and self.search_index != '':
                # if search upward, move the current search position after the previous found position
                self.search_index = f'{self.search_index} + {text_len} chars'

            # search for the next/previous occurence
            if self.search_index == '': self.search_index = '1.0'
            self.search_index = self.txt_help.search(self.text_in_search, self.search_index, backwards = not (search_next))

            if self.search_index != '':
                # show the found text
                self.txt_help.see(self.search_index)
            else:
                messagebox.showinfo(title="Search result", message=f"{self.text_in_search} is not found")

    #-------------------------------------------------------------------------------------------------
    def help_search_text_key_pressed(self, event):
        #--- (GUI event callback) the user has pressed a keyboard key in the text search in help

        # to block temporarily the GUI events caused by the operations done in this function
        self.gui_events_block()

        # remove the selection which appear automatically on the text when an item is selected in a combobox
        self.cmb_search_text.selection_clear()

        # update the status of some GUI widgets
        self.gui_status_do_update()

        if event.keysym == 'Return' and self.cmb_search_text.get() != '':
            self.help_search_next()

    #-------------------------------------------------------------------------------------------------
    images_ref=[]  # list needed to keep in memory the reference to the images opened by PhotoImage and added in the text box, else they are not displayed (Python bug ?)

    def odf_syntax_highlight(self, txt_widget):
        #--- apply syntax highlighting to the content of the given object text box widget

        # remove the tags previously set in the text box
        txt_widget.tag_remove(self.tag_field, '1.0', END)
        txt_widget.tag_remove(self.tag_comment, '1.0', END)
        txt_widget.tag_remove(self.tag_obj_UID, '1.0', END)
        txt_widget.tag_remove(self.tag_title, '1.0', END)

        # put in a list the lines of the text box
        lines = txt_widget.get('1.0', END).splitlines()

        # parse all the characters of the text box lines
        for l in range(0, len(lines)):
            for c in range(0, len(lines[l])):
                if lines[l][0] == ';':  # comment line
                    txt_widget.tag_add(self.tag_comment, f'{l+1}.0', f'{l+1}.0 lineend')
                    break
                elif lines[l][0] == '[' and lines[l][c] == ']':  # object ID
                    txt_widget.tag_add(self.tag_obj_UID, f'{l+1}.0', f'{l+1}.{c+1}')
                    break
                elif txt_widget.get(f'{l + 1}.{c}') == '=':  # equal char in a attribute=value line
                    txt_widget.tag_add(self.tag_field, f'{l+1}.0', f'{l + 1}.{c}')
                    break
                elif lines[l][:2] == '§§' :  # image file name to insert (in the help)
                    # recover the file name after the '§§' tag
                    file_name_str = lines[l][2:]
                    # remove the file name in the widget
                    txt_widget.delete(f'{l+1}.0', f'{l+1}.0 lineend')
                    try:
                        # open the image file
                        photo = PhotoImage(file = os.path.dirname(__file__) + '/' + file_name_str)
                        # add the reference of the image in the list to store these references
                        self.images_ref.append(photo)
                        # insert the image in the text box
                        txt_widget.image_create(f'{l+1}.0', image=photo, padx=10, pady=10)
                    except:
                        # insert a message indicating that the image has not been opened
                        txt_widget.insert(f'{l+1}.0', f'!!! cannot open the image {file_name_str}')
                    break
                elif lines[l][:2] == '>>' :  # title line (in the help)
                    txt_widget.delete(f'{l+1}.0', f'{l+1}.3')
                    txt_widget.tag_add(self.tag_title, f'{l+1}.0', f'{l+1}.0 lineend')
                    break

    #-------------------------------------------------------------------------------------------------
    def check_odf_lines(self):
        #--- check the consistency of the ODF data

        # ask to the user to apply his object data change before to launch the check
        if self.save_modif_before_change(object_change=True):
            # the user has not cancelled the operation

            # do the check
            self.odf_data.check_odf_lines(self.progress_status_update)

            # update the events log text
            self.events_log_text_display()

            # select the Logs tab of the notebook to show the check result
            self.notebook.select(self.frm_logs)

            # restore the object parents label content
            self.object_text_do_parents_update()

    #-------------------------------------------------------------------------------------------------
    def progress_status_update(self, message):
        #--- callback function called by the C_ODF.check_odf_lines or C_HW2GO.GO_ODF_build_from_HW_ODF function
        #--- to display in the parents label widget a progress status message

        self.lab_parents_list.config(text=message)
        self.lab_parents_list['foreground'] = 'red3'
        self.lab_parents_list.update_idletasks()

#-------------------------------------------------------------------------------------------------
class CreateToolTip(object):
    # class to create a tooltip for a given widget
    # tk_ToolTip_class101.py
    # gives a Tkinter widget a tooltip as the mouse is above the widget
    # tested with Python27 and Python34  by  vegaseat  09sep2014
    # www.daniweb.com/programming/software-development/code/484591/a-tooltip-class-for-tkinter
    # Modified to include a delay time by Victor Zaccardo, 25mar16
    # example of usage : tooltip = CreateToolTip(parend_widget, "string to display")
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None
    def enter(self, event=None):
        self.schedule()
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)
    def unschedule(self):
        id = self.id
        self.id = None
        if id: self.widget.after_cancel(id)
    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(self.tw, text=self.text, justify='left',
        background="#ffffff", relief='solid', borderwidth=1,
        wraplength = self.wraplength)
        label.pack(ipadx=1)
    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw: tw.destroy()


#-------------------------------------------------------------------------------------------------
NOTES = ['C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'B']
OCTAVES = list(range(11))
NOTES_IN_OCTAVE = len(NOTES)

def midi_number_to_note(number: int) -> tuple:
    octave = number // NOTES_IN_OCTAVE
    assert octave in OCTAVES, f'Wrong octave {octave} number in midi_number_to_note function'
    assert 0 <= number <= 127, f'Wrong MIDI note number {number} in midi_number_to_note function'
    note = NOTES[number % NOTES_IN_OCTAVE]
    return note, octave

def midi_note_to_number(note: str, octave: int) -> int:
    assert note in NOTES, f'Wrong note name {note} in midi_note_to_number function input'
    assert octave in OCTAVES, f'Wrong octave number {octave} in midi_note_to_number function input'
    note = NOTES.index(note)
    note += (NOTES_IN_OCTAVE * octave)
    assert 0 <= note <= 127, f'Wrong note number {note} in midi_note_to_number function'
    return note

#-------------------------------------------------------------------------------------------------
def myint(string):
    # return the given string in integer format, or None if the given string cannot be converted to integer or is not defined

    if string == None:
        return None

    try:
        return int(string)
    except:
        return None

#-------------------------------------------------------------------------------------------------
def myfloat(string):
    # return the given string in float format, or None if the given string cannot be converted to float or is not defined

    if string == None:
        return None

    try:
        return float(string)
    except:
        return None

#-------------------------------------------------------------------------------------------------
def main():
    #--- main function of the application

    # initiate a C_GUI class instance, display the main window based on this instance, start the main loop of this window
    C_GUI().wnd_main_build().mainloop()

#-------------------------------------------------------------------------------------------------
# first line of code executed at the launch of the script
# if we are in the main execution environment, call the main function of the application
if __name__ == '__main__': main()

