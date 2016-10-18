package peerrest

import (
	"bytes"
	"fmt"
	"io/ioutil"
	//"log"
	"net/http"
	"crypto/tls"
	"os"
	"time"
	"strings"
)

const (
	//waitSecs = 40
	waitSecs = 90
	waitTimeoutRetries = 1
 )

// Calling GetChainInfo according to http or https api according to the value in env variable "TEST_NET_COMM_PROTOCOL"

func GetChainInfo(url string) (respBody string, respStatus string){
	if strings.ToUpper(os.Getenv("TEST_NET_COMM_PROTOCOL")) == "HTTPS" {
		respBody, respStatus = GetChainInfo_HTTPS(url)
	} else  {
		respBody, respStatus = GetChainInfo_HTTP(url)
	}
	return respBody, respStatus
}

/*
  Issue GET request to BlockChain resource
    url is the GET request.
	respStatus is the HTTP response status code and message
	respBody is the HTTP response body
*/
func GetChainInfo_HTTP(url string) (respBody string, respStatus string) {
	//TODO : define a logger
	//fmt.Println("GetChainInfo_HTTP :", url)

	httpclient := &http.Client{ Timeout: time.Second * waitSecs }
	response, err := httpclient.Get(url)

	if err != nil {
		fmt.Println("Error from httpclient.GET request, url, response: ", url, response)
		fmt.Println("Error from httpclient.GET request, err: ", err)
		return err.Error(), "Error from httpclient.GET request"
	} else {
		defer response.Body.Close()
		contents, err := ioutil.ReadAll(response.Body)
		if err != nil {
			fmt.Println("Error from ioutil.ReadAll during GET request, url, response, contents: ", url, response, contents)
			fmt.Println("Error from ioutil.ReadAll during GET request, err: ", err)
			return err.Error(), "Error from ioutil.ReadAll during GET request"
		}
		return string(contents), response.Status
	}
}

/*
  Issue GET request to BlockChain resource
    url is the GET request.
	respStatus is the HTTPS response status code and message
	respBody is the HTTPS response body
*/
func GetChainInfo_HTTPS(url string) (respBody string, respStatus string) {
	//TODO : define a logger
	//fmt.Println("GetChainInfo_HTTPS :", url)

        tr := &http.Transport{
	         TLSClientConfig:    &tls.Config{RootCAs: nil},
	         DisableCompression: true,
        }
        httpsclient := &http.Client{ Timeout: time.Second * waitSecs, Transport: tr }
        response, err := httpsclient.Get(url)
	if err != nil {
			fmt.Println("ERROR from httpsclient.GET request, url, response: ", url, response)
			fmt.Println("ERROR from httpsclient.GET request, err: ", err)
			return err.Error(), "ERROR from httpsclient.GET request"
	} else {
		defer response.Body.Close()
		contents, err := ioutil.ReadAll(response.Body)
	        if err != nil {
			fmt.Println("ERROR from https ioutil.ReadAll during GET request, url, response, contents: ", url, response, contents)
			fmt.Println("ERROR from https ioutil.ReadAll during GET request, err: ", err)
			return err.Error(), "ERROR from https ioutil.ReadAll during GET request"
		}
		return string(contents), response.Status
	}
}

// Calling GetChainInfo according to http or https api according to the value in env variable "TEST_NET_COMM_PROTOCOL"

func PostChainAPI(url string, payLoad []byte) (respBody string, respStatus string){
	if strings.ToUpper(os.Getenv("TEST_NET_COMM_PROTOCOL")) == "HTTPS" {
		respBody, respStatus = PostChainAPI_HTTPS(url, payLoad)
	} else  {
		respBody, respStatus = PostChainAPI_HTTP(url, payLoad)
	}
	return respBody, respStatus
}

/*
  Issue POST request to BlockChain resource.
	url is the target resource.
	payLoad is the REST API payload
	respStatus is the HTTP response status code and message
	respBody is the HHTP response body
*/
func PostChainAPI_HTTP(url string, payLoad []byte) (respBody string, respStatus string) {


	req, err := http.NewRequest("POST", url, bytes.NewBuffer(payLoad))
	//req.Header.Set("X-Custom-Header", "myvalue")
	req.Header.Set("Content-Type", "application/json")

	httpclient := &http.Client{ Timeout: time.Second * waitSecs }
	response, err := httpclient.Do(req)
	if err != nil {
		// response is likely nil, since err is not nil. Print whatever we can to help debug.
		fmt.Println("PostChainAPI() httpclient.Do Error: url: ", url)
		fmt.Println("PostChainAPI() httpclient.Do Error: payLoad: ", string(payLoad))
		fmt.Println("PostChainAPI() httpclient.Do Error: err: ", err)
		fmt.Println(">>>Things to check, in order:\n - the response and err returned (above)\n - the correct Network Credentials file\n - command is sending to the correct IP Address")
		fmt.Println(" - check if your network connection (wired or wireless?) dropped, especially if using a non-local network")
		fmt.Println(" - check if any problem with a firewall/router or other hop in the network path from here to the specified destination")
		return err.Error(), "httpclient.Do Error"
	}
	// Response is likely not nil, since err is nil.
	defer response.Body.Close()
	// use ReadAll and string() to translate the response body into a string
	body, readall_err := ioutil.ReadAll(response.Body)
	if readall_err != nil {
		fmt.Println("PostChainAPI() Error from ioutil.ReadAll() translating httpclient.Do response.Body; url: ", url)
		fmt.Println("PostChainAPI() Error from ioutil.ReadAll() err: ", readall_err)
		return readall_err.Error(), "ERROR from ioutil.ReadAll while translating response.Body from httpclient.Do"
	}
	//return string(body), response.Status
	return string(body), string("")
}

/*
  Issue POST request to BlockChain resource.
	url is the target resource.
	payLoad is the REST API payload
	respStatus is the HTTP response status code and message
	respBody is the HHTP response body
*/
func PostChainAPI_HTTPS(url string, payLoad []byte) (respBody string, respStatus string) {

        tr := &http.Transport{
                 TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	         //TLSClientConfig:    &tls.Config{RootCAs: nil},
	         DisableCompression: true,
        }
        httpclient := &http.Client{ Transport: tr, Timeout: time.Second * waitSecs }
	response, err := httpclient.Post(url, "json", bytes.NewBuffer(payLoad))
	if err != nil {
		// response is likely nil, since err is not nil. Print whatever we can to help debug.
		fmt.Println("PostChainAPI_HTTPS() httpclient.Post Error: url: ", url)
		fmt.Println("PostChainAPI_HTTPS() httpclient.Post Error: payLoad: ", string(payLoad))
		fmt.Println("PostChainAPI_HTTPS() httpclient.Post Error: err: ", err)
		return err.Error(), "httpclient.Post Error"
	}
	// response is likely not nil, since err is nil.
	defer response.Body.Close()
	// use ReadAll and string() to translate the response body into a string
	body, readall_err := ioutil.ReadAll(response.Body)
	if readall_err != nil {
		fmt.Println("PostChainAPI_HTTPS Error from ioutil.ReadAll while translating response.Body; url: ", url)
		fmt.Println("PostChainAPI_HTTPS Error from ioutil.ReadAll, readall_err: ", readall_err)
		return readall_err.Error(), "ERROR from ioutil.ReadAll while translating response.Body from httpclient.Post"
	}
	//return string(body), response.Status
	return string(body), string("")
}
