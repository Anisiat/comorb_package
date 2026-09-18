
# Module information 

## Cleaning 

takes in raw tables cleans and standardises them 

diagnoses have a lot of missing dates which can be inputed by matching on spell ids and using admission dates as proxy 

keeps track of evidence data and source 

## Mapping

Maps ICD 10 and SNOMED codes from lookups + uses medication to innfer some comorbidities 
importantly - always returns same schema for all tables so they can later be merged into a long table with all the comorbidity information 
for each patient - keeping track of what the source of info was (also keeps track of snomed or icd code?) + evidence date 
