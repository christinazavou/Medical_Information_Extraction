# Medical_Information_Extraction

#### usage
call main.py aux_config\confxx.yml data_folder_path results_folder_path

check aux_config\sample_configuration.yml to see how the setup is set
and used.

#### In read_data.py:
read_patients() calls patient2json() where it checks whether the patient 
folder contains a report csv that is not empty.

#### In store_data.py:
store_deceases() stores for each decease folder given, all of its 
patients (found in the jsons folder) -index_es_patients()-, and also 
stores the forms with their fields and patient ids -index_form()- and 
puts the form values to the indexed patients -put_forms_in_patients().

#### In pre_process.py:
this is used when we want to copy the patient indexed documents and 
re-index them as pre-processed ones.

