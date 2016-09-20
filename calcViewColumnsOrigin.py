# Software licensed by the MIT License of Open Source (https://opensource.org/licenses/MIT)

import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
import pyhdb
import xml.etree.ElementTree as ET
import sys
import time
import json

# Change here the connection parameters for your HANA System
host = "0.0.0.0"
port = 30015
user = "USER"
pswd = "PASS"

# Receives the CDATA XML from a view and parses it in a specific structure
def parseCalc(view,cData,cursor):
	xml = ET.fromstring(cData)

	# Process all the sources from the CalcView
	sources = {}
	for child in xml.iter('DataSource'):
		for grandchild in child:
			source = {}
			source['type'] = child.attrib['type']
			if grandchild.tag == 'columnObject':
				source['name'] = grandchild.attrib['columnObjectName']
				source['path'] = grandchild.attrib['schemaName']
			elif grandchild.tag == 'resourceUri':
				source['name'] = grandchild.text.split("/",3)[3]
				source['path'] = grandchild.text.split("/",3)[1]
			sources[child.attrib['id']] = source

	# Process all the outputs from the CalcView
	outputs = {}
	for child in xml.iter('attribute'):
		for grandchild in child.iter('keyMapping'):
			output = {}
			output['source'] = grandchild.attrib['columnName']
			output['node'] = grandchild.attrib['columnObjectName']
			output['type'] = 'column'
			outputs[child.attrib['id']] = output

	for child in xml.iter('calculatedAttribute'):
		for grandchild in child.iter('formula'):
			output = {}
			output['source'] = grandchild.text
			output['node'] = '$FORMULA$'
			output['type'] = 'formula'
			outputs[child.attrib['id']] = output

	# Process all the nodes from the CalcView
	nodes = {}
	for child in xml.iter('calculationView'):
		node = {}
		node['type'] = child.attrib['xsitype']	
		nodeSources = {}	
		sourceColumns = {}
		sourceFormulas = {}

		for grandchild in child.iter('input'):
			inputSource = {}
			for grandgrandchild in grandchild.iter('mapping'):
				if grandgrandchild.get('source'):
					column = {}
					column['type'] = 'column'
					column['source'] = grandgrandchild.attrib['source']
					inputSource[grandgrandchild.attrib['target']] = column
			nodeSources[grandchild.attrib['node'][1:]] = inputSource

		for grandchild in child.iter('calculatedViewAttribute'):
			inputSource = {}
			for grandgrandchild in grandchild.iter('formula'):
				column = {}
				column['type'] = 'formula'
				column['source'] = grandgrandchild.text
				inputSource[grandchild.attrib['id']] = column
			sourceFormulas[grandchild.attrib['id']] = column

		if sourceFormulas:
			nodeSources['$FORMULA$'] = sourceFormulas
		node['sources'] = nodeSources
		nodes[child.attrib['id']] = node

	parsedCalc = {
		'viewName': view, 
		'sources': sources,
		'outputs': outputs,
		'nodes': nodes
	}

	return parsedCalc

# Based on the structure defined, find the Source Node from a column
def findSourceNode(column,node,calcView):
	if node in calcView['nodes']:
		for originSource in calcView['nodes'][node]['sources'].keys():
			if originSource in calcView['nodes'][node]['sources']:
				if column in calcView['nodes'][node]['sources'][originSource]:
					return {
						'column': calcView['nodes'][node]['sources'][originSource][column]['source'],
						'sourceNode': originSource,
						'columnType': calcView['nodes'][node]['sources'][originSource][column]['type'],
						'parentNode': node
					}

# Find the source of a single Column in a CalcView Structure 
def findColumnSource(calcView, column):
	columnSource = {'source': ''}
	if (calcView['outputs'][column]['node'] == '$FORMULA$'):
		columnSource = {
			'source': calcView['outputs'][column]['node'],
			'column': calcView['outputs'][column]['source'],
			'sourceType': calcView['outputs'][column]['type'],
			'sourcePath': ''
		}
	else:
		currentNode = findSourceNode(calcView['outputs'][column]['source'], calcView['outputs'][column]['node'], calcView)
		while (columnSource['source'] == ''):
			if (currentNode['sourceNode'] in calcView['sources']):
				columnSource = {
					'column': currentNode['column'],
					'source': calcView['sources'][currentNode['sourceNode']]['name'],
					'sourceType': calcView['sources'][currentNode['sourceNode']]['type'],
					'sourcePath': calcView['sources'][currentNode['sourceNode']]['path']
				}	
			elif currentNode['sourceNode'] == '$FORMULA$':
				columnSource = {
					'column': currentNode['column'],
					'source': currentNode['parentNode'],
					'sourceType': currentNode['columnType'],
					'sourcePath': calcView['viewName']
				}
			else:
				currentNode = findSourceNode(currentNode['column'], currentNode['sourceNode'], calcView)
	return columnSource

# Find the source of all columns from a CalcView Structure
def allColumnsOrigin(view):
	totalTime = time.time()			
	print('Starting connection...')
	startTime = time.time()
	connection = pyhdb.connect(host = host, port = port, user = user, password = pswd )
	print('Connection estabilished! Time taken:', round((time.time()-startTime)*1000,2),'miliseconds')

	# Executes a query for all the CalcView dependencies
	cursor = connection.cursor()
	sql = "SELECT PACKAGE_ID||'/'||OBJECT_NAME, REPLACE(TO_NVARCHAR(CDATA),'xsi:type','xsitype') FROM \"_SYS_REPO\".\"ACTIVE_OBJECT\" WHERE PACKAGE_ID||'/'||OBJECT_NAME IN (SELECT BASE_OBJECT_NAME FROM \"PUBLIC\".\"OBJECT_DEPENDENCIES\" WHERE DEPENDENT_OBJECT_NAME = '"+ view +"' AND BASE_OBJECT_TYPE = 'VIEW') OR PACKAGE_ID||'/'||OBJECT_NAME = '"+ view +"'" 
	
	print('Executing query...')
	startTime = time.time()
	cursor.execute(sql)
	print('Query executed! Time taken:', round((time.time()-startTime)*1000,2),'miliseconds')
	result = cursor.fetchone()
	
	if(result):
		parsedViews = {}

		print('Parsing Views...')
		startTime = time.time()
		while result:
			viewCData = parseCalc(result[0],result[1],cursor)
			parsedViews[result[0].split("/")[1]] = viewCData
			result = cursor.fetchone()
		print('Views parsed! Time taken:', round((time.time()-startTime)*1000,2),'miliseconds')

		columnsOrigin = {}
		currentView = view.split("/")[1]

		print('Parsing Columns...')
		startTime = time.time()
		for output in parsedViews[currentView]['outputs']:
			continueSearch = 1
			currentColumn = output
			# print('Getting origins from',currentColumn)
			while continueSearch == 1:
				origin = findColumnSource(parsedViews[currentView],currentColumn)
				if origin['sourceType'] == 'DATA_BASE_TABLE' or origin['sourceType'] == 'formula':
					columnsOrigin[output] = origin
					continueSearch = 0
				else:
					currentView = origin['source']
					currentColumn = origin['column']

			currentView = view.split("/")[1]
		print('Columns parsed! Time taken:', round((time.time()-startTime)*1000,2),'miliseconds')
		res = columnsOrigin
		
	else:
		res = { 'error': 'View '+ view +' not found. Please, check the name.'}
		print(res['error'])
	
	print('Writing file...')
	f = open('resultCalcViewColumnsOrigin.json', 'w')
	f.write(str(json.dumps(res)))
	f.close()

	print('Closing connection...')
	connection.close()
	print('Finished! Time taken: ', round((time.time()-totalTime),4),'seconds')

# If you want just wanna call the function withou the UI comment everything below and run this:
# allColumnsOrigin('<view>')

# Just a simple handler and HTTP Server set up
class MyHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		if '/calcViewColumnsOrigin' in self.path:
			p = self.path.split("?")
			print(p)
			params = {}
			params = urllib.parse.parse_qs(p[1], True, True)
			print(params)
			print('Starting Columns Origin JSON with ',params['object'][0])
			allColumnsOrigin(params['object'][0])
			print('Finished Columns Origin JSON')

		if '/columnsOrigin' in self.path:
			f = open('columnsOrigin.html','rb')
			self.send_response(200)
			self.send_header('Content-type','text-html')
			self.end_headers()
			self.wfile.write(f.read())
			f.close()

		if self.path == '/resultCalcViewColumnsOrigin':
			f = open('resultCalcViewColumnsOrigin.json','rb')
			self.send_response(200)
			self.wfile.write(f.read())
			f.close()

def run():
  print('http server is starting...')
  httpd = HTTPServer(("", 5001), MyHandler)
  print('http server is running...')
  httpd.serve_forever()
  
if __name__ == '__main__':
  run()   