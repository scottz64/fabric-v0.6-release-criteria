#!/usr/bin/python
import time
import sys
import requests
import json
import threading
import Queue

from optparse import OptionParser


class EQueue(Queue.Queue):

    def is_empty(self):
        try:
            for item in self.queue:
                if item == ('stop', ()):
                    self.queue.remove(item)
        except:
            pass
        if self.qsize() == 0:
            return True
        return False

    def join_with_timeout(self, timeout):
        self.all_tasks_done.acquire()
        try:
            endtime = time.time() + timeout
            while retval == 0:
                retval = self._loop_it(endtime)
                if retval == 1:
                    raise Exception
        except:
            pass
        finally:
            self.all_tasks_done.release()

    def _loop_it(self, endtime, failure_cnt=0):
        while self.unfinished_tasks:
            remaining = endtime - time.time()
            if remaining <= 0.0:
                failure_cnt = failure_cnt +1
                break
            self.all_tasks_done.wait(remaining)
        return failure_cnt


def handleOptions():
    '''Handle options'''
    parser = OptionParser(description='Performance testing of Fabric.')
    parser.add_option("-j", "--junit", dest="junit", action="store_true", default=False,
                      help="display output in Junit format")
    parser.add_option("-o", "--outfile", dest="outfile", default="results.xml",
                      help="output file to store the results", metavar="OUT_FILE")
    parser.add_option("-i", "--input", dest="infile", default="service_creds.json",
                      help="input file containing network data", metavar="INPUT_FILE")
    parser.add_option("-c", "--count", dest="count", default=1000, type="int",
                      help="number of invokes and queries to transmit", metavar="COUNT")
    parser.add_option("-t", "--threads", dest="threads", default=1, type="int",
                      help="number of threads to spawn for sending calls to the network")
    parser.add_option("-z", "--hsbn", dest="hsbn", action="store_true", default=False,
                      help="indicates this is on an HSBN network")

    (options, args) = parser.parse_args()
    return options


def pullServiceCreds(network_id):
    '''Pull the service credentials file based on the network ID entered'''
    headers = {'Accept': 'application/json', 'Content-type': 'application/json'}
    resp = requests.get("https://obc-service-broker-prod.mybluemix.net/api/network/%s"%network_id, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    print "Unable to access the service credentials page. %d(%s): %s" % (resp.status_code, resp.reason, str(resp.content))


def readNetworkFile(network_file):
    '''Read the network file'''
    # Prompt if data is not present
    if network_file is None:
        network_file = raw_input("Please enter the name of the network file: ")

    # Read the given network file
    with open(network_file, "r") as fd:
        network_info = json.loads(fd.read())
    if 'credentials' in network_info.keys():
        return network_info['credentials']
    return network_info

 
def get_valid_users(users):
    '''Gather user data from the network file'''
    user_info = []

    for user in users:
        if user['username'].startswith("user_type1"):
            user_info.append(dict(username=user['username'], secret=user['secret']))
    return user_info


def saveXMLFile(data, options):
    '''Write xml output file for junit output'''
    with open(options.outfile, "w") as fd:
       fd.write(json.dumps(data, indent=3))

def doit(q, url, headers, payload):
    try:
        resp = requests.request("POST", url, data=json.dumps(payload), headers=headers, verify=False)
        #resp = requests.request("POST", url, data=json.dumps(payload), headers=headers, timeout=2, verify=False)
        q.put(('ok', resp))
    except Exception, err:
        pass
        q.put(('err', err))
        #print sys.exc_info()
        #print ""


def process_response(q, action, count, response):
    while True:
        try:
            flag, item = q.get(True, 5)
            if flag == 'stop':
                break
            response.put(item)
            with open("debug.out", "a") as fd:
                fd.write("%s: %r\n" % (action, item.json()))
                fd.close()
            item.connection.close()
        except:
            break
    if q.unfinished_tasks:
        q.task_done()

def start_response_threads(num_threads, data):
    pool = []
    for i in range(num_threads):
         t = threading.Thread(target=process_response, args=data)
         t.daemon = True
         t.start()
         pool.append(t)
    return pool

def start_request_threads(num_threads, q_in):
    pool = []
    for i in range(num_threads):
         t = threading.Thread(target=process_requests, args=(q_in, ))
         t.daemon = True
         t.start()
         pool.append(t)
    return pool

def process_requests(q_in):
    while True:
        flag, data = q_in.get()
        if flag == 'stop':
            break
        (q, url, headers, payload) = data
        doit(q, url, headers, payload)
    q_in.task_done()

def stop_threads(thread_pool, q_in):
    for i in thread_pool:
        q_in.put(("stop", ()))
    while len(thread_pool) != 0:
        for the_thread in thread_pool:
            if not q_in.is_empty():
                continue
            else:
                index = thread_pool.index(the_thread)
                del thread_pool[index]
            break

def post_chaincode(network_info, action, params, count, options):
    url = "%s/chaincode" % network_info['peers'][0]['api_url']
    headers = {'Content-Type': "application/json",
               'Accept': "application/json"}
    if options.hsbn:
        headers['zACI-API'] = 'com.ibm.zaci.system/1.0'
        url = url.replace("http", "https")

    payload = {"jsonrpc": "2.0",
               "method": action,
               "params": params,
               "id": 0}

    q = EQueue()
    response = Queue.Queue()
    q_in = EQueue()

    request_pool = start_request_threads(options.threads, q_in)
    response_pool = start_response_threads(options.threads, (q, action, count, response))

    start = time.time()
    for i in range(count):
        q_in.put(("ok", (q, url, headers, payload)))
    q_in.put(("stop", ()))

    stop_threads(request_pool, q_in)
    stop_threads(response_pool, q)
    end = time.time() - 2

    time.sleep(5)

    responseL = []
    err_count = 0
    for x in range(response.qsize()):
        r = response.get()
        r.connection.close()
        try:
            if r.status_code != 200:
                err_count = err_count + 1
        except:
            print r
            err_count = err_count + 1
        responseL.append(r)

#    for r in responseL:
#        try:
#            if r.status_code != 200:
#                err_count = err_count + 1
#        except:
#            print r
#            err_count = err_count + 1

    print "... Number of '%s' errors (Total: %d): %d" % (action, count, err_count) 
    return start, end, responseL

def deploy(network_info, users, options):
    params = {"type": 1,
              "chaincodeID": {"path": "github.com/hyperledger/fabric/examples/chaincode/go/chaincode_example02",
                              "name": ""},
              "ctorMsg": {"function": "init",
                          "args":["a", "3000", "b", "2500"]},
              "secureContext": users[0]['username']}
    response = post_chaincode(network_info, "deploy", params, 1, options)
    return response[2][0]


def register(network_info, users, options):
    response = []
    for peer in network_info['peers']:
        index = network_info['peers'].index(peer)
        url = "%s/registrar" % peer['api_url']
        headers = {'Content-Type': "application/json",
                   'Accept': "application/json"}
        if options.hsbn:
            headers['zACI-API'] = 'com.ibm.zaci.system/1.0'
            url = url.replace("http", "https")

        payload = {"enrollId": users[index]['username'],
                   "enrollSecret": users[index]['secret']}

        response.append(requests.request("POST", url, data=json.dumps(payload), headers=headers, timeout=2, verify=False))
    return response

def query(network_info, users, options, chaincodeId):
    params = {"type": 1,
              "chaincodeID":{"name":chaincodeId},
              "ctorMsg": {"function": "query",
                          "args":["b"]},
              "secureContext": users[0]['username']}
    return post_chaincode(network_info, "query", params, options.count, options)

def invoke(network_info, users, options, chaincodeId):
    params = {"type": 1,
              "chaincodeID":{"name": chaincodeId},
              "ctorMsg": {"function":"invoke",
                          "args":["a", "b", "10"]},
              "secureContext": users[0]['username']}
    return post_chaincode(network_info, "invoke", params, options.count, options)

def calculate(count, start, end):
    diff_time = end - start
    print "Diff time:", diff_time
    tps = float(count / diff_time)
    return tps

def main():
    options = handleOptions()
    print "Reading service network file %s." % options.infile
    network_info = readNetworkFile(options.infile)
    users = get_valid_users(network_info['users'])
    register(network_info, users, options)
    print "Users registered."
    resp = deploy(network_info, users, options)
    print "Chaincode deployed."
    try:
        chaincodeId = resp.json()['result']['message']
    except:
        print resp.json()
        sys.exit()

    print "Query the chaincode %d times." % options.count
    q_start, q_end, q_response = query(network_info, users, options, chaincodeId)
    q_tps = calculate(options.count, q_start, q_end)
    print "Query TPS:", q_tps
    time.sleep(2)
    print ""
    print "Invoke the chaincode %d times." % options.count
    i_start, i_end, i_response = invoke(network_info, users, options, chaincodeId)
    i_tps = calculate(options.count, i_start, i_end)
    print "Invoke TPS:", i_tps

    print "Save resulting data to file: %s." % options.outfile
    data = {"queries": q_tps,
            "invokes": i_tps,
            "count": options.count}
    saveXMLFile(data, options)

if __name__ == "__main__":
    main()
