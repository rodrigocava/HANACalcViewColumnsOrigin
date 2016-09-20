# HANA Calculation View Columns Origin
Find the Origin of every column in a HANA Calculation View

This simple development generates a JSON with the origin of all the columns of a SAP HANA Calculation View. It is useful when you have a lot of different dependent tables, formulas or views.

## Utilization
  1. Edit the file calcViewColumnsOrigin.py file and add your HANA DB information (the variables are at the top, after the imports): 
    - host 
    - port
    - user
    - password
  2. At a python terminal, go to the project folder and run calcViewColumnsOrigin.py local server with the comand:
  
      ``` python3 calcViewColumnsOrigin.py ```

  3. Open in your browser the following link: [http://localhost:5001/columnsOrigin](http://localhost:5001/columnsOrigin)
  4. Enter the full name of a Calculation View (< package >.< subpackages >/< viewName >) at the textInput
  5. Hit "Enter" or press the "Find Origin!" button. A JSON should appear bellow the button

The structure that it generates is the follow:

    { 
      <COLUMN NAME>: {
        "sourceType": <Shows "DATA_BASE_TABLE" for table columns and "formula" for Formulas>,
        "source": <Shows table name for table columns and the Calculation View Node for Formulas>,
        "column": <Shows column name for table columns and the formula for Formulas>,
        "source": <Shows schema name for table columns and the Calculation View Name for Formulas>
      }
    } 


[![columnsOrigin.png](http://s9.postimg.org/d861gd7kv/columns_Origin.png)](http://postimg.org/image/ae2w2x5ej/)


## Architecture
I used a Python script that have a function to connect to the HANA DB (many thanks for this [post]( https://github.com/SAP/PyHDB)) and also generates a simples HTTP server to run the UI in HTML + JS. The function generates a external file (called resultCalcViewColumnsOrigin.json) that is read by the HTML using jQuery ([this one](https://stackoverflow.com/questions/4810841/how-can-i-pretty-print-json-using-javascript)). I made it this way because you can also use the .JSON file generated in other documentations as well.

The function check the dependencies at the PUBLIC Schema table called **OBJECT_DEPENDENCIES** and get all the CalcViews XML from **ACTIVE_OBJECTS**. It's important to notice that a query from this table will only show the records that your user have permisson, so make sure to check your user's permission if you ran into any weird situations.

Also make sure to check the information about of yours HANA System **ports** when your using a Multitenant DB. Check this [link](https://help.sap.com/saphelp_hanaplatform/helpdata/en/44/0f6efe693d4b82ade2d8b182eb1efb/frameset.htm) in case you run in some sort of trouble.

## TO DOs

* Join this development with my other [HANA Calculation View Hierarchy Graph](https://github.com/rodrigocava/HANAcalcViewHierarchy)

