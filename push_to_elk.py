#!/usr/bin/python3
import sys
import time
import json
import tqdm
import hashlib
import argparse
import datetime
import elasticsearch

# Simple iterator yielding all the LDIF records one by one.
def yieldrecords(stream,skipfast=0):
  record = ''
  for line in stream:
    # New records begin with a "#"
    if line[0] == '#':
      # This means we have to yield the previous record
      if len(record.strip()) != 0:
        if skipfast > 0:
          skipfast = skipfast - 1
          yield None
        else:
          yield record
      # And reset the state
      record = ''
    else:
      # Otherwise, append the line
      if len(line.strip()) != 0:
        record += line
  # Don't forget to yield the last record
  yield record

class Element:
  def __init__(self,block):
    self.properties = {}
    self.properties['x_imported_on'] = time.strftime('%Y-%m-%d-%H-%M-%S')
    # At Element creation, we split the block in lines and create as much ptoperties as needed
    for line in block.splitlines():
      # Worst approach at dealing with the base64-encoded entries
      try:
        key, value = line.strip().split(': ',1)
      except:
        key, value = line.strip().split(':',1)

      # Worst approach at dealing with strangely named entries
      if ':' in key:
        key = key.split(':')[0]

      # Handling those strange timestamps formats by creating some _UNIX timestamp keys
      # and converting the raw .0Z values in actual integer timestamps.
      if (len(value) == 17) and (value[-3:] == '.0Z'):
        try:
          value = int(time.mktime(time.strptime(value,"%Y%m%d%H%M%S.0Z")))
          self.add_property(key+"_UNIX",time.strftime("%Y-%m-%d-%H-%M-%S",time.gmtime(value)))
        except ValueError:
          value = 0

      # We know that some keys are integers, and want
      # them to be stored as integers within elasticsearch
      if key in ['accountExpires','adminCount','appSchemaVersion','badPasswordTime','badPwdCount','carLicense','codePage','countryCode','deliveryMechanism','dLMemDefault','flags','instanceType','internetEncoding','lastLogoff','lastLogon','lastLogonTimestamp','lastUpdateSequence','localeID','localPolicyFlags','lockoutTime','logonCount','primaryGroupID','priority','pwdLastSet','revision','sAMAccountType','versionNumber']:
        value = int(value)

      if type(value) == int:
        # Special case for the special "number of 100 nanoseconds since 1601-01-01" timestamps
        # 1917 - 2234
        if 100000000000000000 < value < 200000000000000000:
          value = datetime.datetime(1601,1,1) + datetime.timedelta(seconds=(value/10000000))
          value = int(value.strftime("%s"))
          self.add_property(key+"_w32",time.strftime("%Y-%m-%d-%H-%M-%S",time.gmtime(value)))

      self.add_property(key,value)

  def add_property(self,key,value):
    # Simple fail-safe function to add key-values to the 'self.properties' storage
    existing = self.properties.get(key)
    # If it does not exist, create it
    if existing is None:
      self.properties[key] = value
    # If it does exist, but is a string, we'll need a list with the two elements
    elif type(existing) is str:
      self.properties[key] = [self.properties.get(key), value]
    # If it's already a list, then just append another value
    elif type(existing) is list:
      self.properties[key].append(value)
  
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--skip',help='skip N entries',type=int,default=0)
  parser.add_argument('--total',help='skip N entries',type=int)
  args = parser.parse_args()
  
  # Instanciate an elasticsearch client, defaulting its destination to localhost
  es = elasticsearch.client.Elasticsearch()

  count = 0
  for i in tqdm.tqdm(yieldrecords(sys.stdin,skipfast=args.skip),total=args.total,ascii=True):
    # Simple skip for debugging repeated attempts
    if i is None:
      continue

    try:
      element = Element(i)
    except Exception as e:
      print('Invalid data !')
      print(i)
      raise e
    try:
      # Inform elasticsearch of the nature of this object
      if element.properties.get('objectClass') is None:
        doctype = 'no_objectClass'
      else:
        doctype = '-'.join(sorted(set(element.properties.get('objectClass'))))

      # Use the AD objectGUID as elasticsearch GUID
      elk_id = element.properties.get('objectGUID')
      # If the element has no objectGUID, take the SHA1 of the distinguished name
      if element.properties.get('dn') is None:
        # Object has no DN : that's not interesting.
        continue
      elk_id = hashlib.sha1(bytes(element.properties.get('dn'),'utf-8')).hexdigest()

      # Push the data in the database
      es.index(
          index="ad_data",
          doc_type=doctype,
          id=element.properties.get('objectGUID'),
          body=element.properties,)

    except elasticsearch.exceptions.RequestError as e:
      print(json.dumps(element.properties,indent=2))
      print(e)
      raise e
