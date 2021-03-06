import requests
import base64
import yaml
import json
import os.path

action_api_uri_dic = {}
access_token = ''
creds = {}
api_url = "https://ocm-apis-cloud.oracle.com/"
form_data_api_headers = ''
api_headers = ''

class Config:

    listingVersionId = None
    artifactId = None
    packageVersionId = None
    termsId = None
    termsVersionId = None
    action = None
    access_token = None
    imageOcid = None
    credsFile = None
    metadataFile = None
    versionString = None

    def __init__(self, partnerName, credsFile):
        if self.access_token is None:
            set_access_token(partnerName, credsFile)

def bind_action_dic(config):
    global action_api_uri_dic
    action_api_uri_dic = {
        "get_listingVersions": "appstore/publisher/v1/listings",
        "get_listingVersion": f"appstore/publisher/v1/applications/{config.listingVersionId}",
        "get_artifacts": "appstore/publisher/v1/artifacts",
        "get_artifact": f"appstore/publisher/v1/artifacts/{config.artifactId}",
        "get_applications": "appstore/publisher/v1/applications",
        "get_application": f"appstore/publisher/v1/applications/{config.listingVersionId}",
        "get_listing_packages": f"appstore/publisher/v2/applications/{config.listingVersionId}/packages",
        "get_application_packages": f"appstore/publisher/v2/applications/{config.listingVersionId}/packages",
        "get_application_package": f"appstore/publisher/v2/applications/{config.listingVersionId}/packages/{config.packageVersionId}",
        "get_terms": "appstore/publisher/v1/terms",
        "get_terms_version": f"appstore/publisher/v1/terms/{config.termsId}/version/{config.termsVersionId}",
        "create_listing": f"appstore/publisher/v1/applications",
        "create_new_version": f"appstore/publisher/v1/applications/{config.listingVersionId}/version",
        "new_package_version": f"appstore/publisher/v2/applications/{config.listingVersionId}/packages/{config.packageVersionId}/version",
        "upload_icon": f"appstore/publisher/v1/applications/{config.listingVersionId}/icon",
    }

def set_access_token(partnerName, credsFile):
    global access_token
    global creds
    global api_headers

    if partnerName is not None and os.path.isfile(partnerName + "_creds.yaml"):
        with open(partnerName + "_creds.yaml", 'r') as stream:
            creds = yaml.safe_load(stream)
    else:
        with open(credsFile, 'r') as stream:
            creds = yaml.safe_load(stream)

    auth_string = creds['client_id']
    auth_string += ':'
    auth_string += creds['secret_key']

    encoded = base64.b64encode(auth_string.encode('ascii'))
    encoded_string = encoded.decode("ascii")

    token_url = "https://login.us2.oraclecloud.com:443/oam/oauth2/tokens?grant_type=client_credentials"

    auth_headers = {'Content-Type': 'application/x-www-form-urlencoded', 'charset': 'UTF-8',
                    'X-USER-IDENTITY-DOMAIN-NAME': 'usoracle30650',
                    'Authorization': f"Basic {encoded_string}"}

    r = requests.post(token_url, headers=auth_headers)

    access_token = json.loads(r.text).get('access_token')

    api_headers = {'charset': 'UTF-8',
                             'X-Oracle-UserId': creds['user_email'], 'Authorization': f"Bearer {access_token}"}


def do_get_action(config):
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    r = requests.get(uri, headers=api_headers)
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json

def get_new_versionId(config):
    config.action = "create_new_version"
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    api_headers['Content-Type'] = 'application/json'
    r = requests.post(uri, headers=api_headers)
    del api_headers['Content-Type']
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["entityId"]

def update_version_metadata(config, newVersionId):
    config.action = "get_listingVersion"
    config.listingVersionId = newVersionId
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    body_start = '{'
    body_end = '}'
    body = ""

    if not os.path.isfile(config.metadataFile):
        config.versionString = "No Version"
        return f"metadata file {config.metadataFile} not found. skipping metadata update."
    with open(config.metadataFile,  "r") as stream:
        metadata = yaml.safe_load(stream)

    config.versionString = metadata['version']
    del metadata['version']

    for k, v in metadata.items():
        v = v.replace('"',"'")
        body += f""""{k}": "{v}","""

    body = body_start + body
    body = body[:len(body) - 1]
    body = body + body_end
    body = body.encode("unicode_escape").decode("utf-8")

    api_headers['Content-Type'] = 'application/json'
    r = requests.patch(uri, headers=api_headers, data=body)
    del api_headers['Content-Type']
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    if "message" in r_json:
        return r_json["message"]
    else:
        return r.text

def get_packageId(config, newVersionId):
    config.action = "get_application_packages"
    config.listingVersionId = newVersionId
    r = do_get_action(config)
    return r["items"][0]["Package"]["id"]

def get_new_packageVersionId(config, newVersionId, packageId):
    config.action = "new_package_version"
    config.listingVersionId = newVersionId
    config.packageVersionId = packageId
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    api_headers['Content-Type'] = 'application/json'
    r = requests.patch(uri, headers=api_headers)
    del api_headers['Content-Type']
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["entityId"]

def update_versioned_package_version(config, newPackageVersionId):
    config.action = "get_application_package"
    config.packageVersionId = newPackageVersionId
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    body = '{"version": "' + config.versionString + '", "description": "Description of package", "serviceType": "OCIOrchestration"}'
    payload = {'json': (None, body)}
    r = requests.put(uri, headers=api_headers, files=payload)
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["message"]

def create_new_stack_artifact(config, fileName):
    config.action = "get_artifacts"
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    body = '{"name": "' + config.versionString + '", "artifactType": "TERRAFORM_TEMPLATE"}'
    payload = {'json': (None, body)}
    index = fileName.rfind("/")
    name = fileName[index+1:]
    files = {'file': (name, open(fileName, 'rb'))}
    r = requests.post(uri, headers=api_headers, files=files, data=payload)
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["entityId"]

def create_new_image_artifact(config, old_listing_artifact_version):
    config.action = "get_artifacts"
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    if old_listing_artifact_version is not None:
        new_version = {key:old_listing_artifact_version[key] for key in ['name', 'artifactType', 'source', 'artifactProperties']}
        new_version['name'] = config.versionString
        new_version['source']['uniqueIdentifier'] = config.imageOcid
        new_version["artifactType"] = "OCI_COMPUTE_IMAGE"
        body = json.dumps(new_version)
    else:
        file_name = "/newImage.json" if os.path.isfile("/newImage.json") else "newImage.json"
        with open(file_name, "r") as file_in:
            body = file_in.read()
        body = body.replace("%%NAME%%", config.versionString)
        body = body.replace("%%OCID%%", config.imageOcid)

    api_headers['Content-Type'] = 'application/json'
    r = requests.post(uri, headers=api_headers, data=body)
    del api_headers['Content-Type']
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["entityId"]

def associate_artifact_with_package(config, artifactId, newPackageVersionId):

    file_name = "/newArtifact.json" if os.path.isfile("/newArtifact.json") else "newArtifact.json"
    with open(file_name, "r") as file_in:
        body = file_in.read()
    body = body.replace("%%ARTID%%", artifactId)
    body = body.replace("%%VERS%%", config.versionString)

    if config.imageOcid is not None:
        body = body.replace("Orchestration", "")
        body = body.replace("terraform", "ocimachineimage")

    payload = {'json': (None, body)}
    config.action = "get_application_package"
    config.packageVersionId = newPackageVersionId
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    r = requests.put(uri, headers=api_headers, files=payload)
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["message"]

def submit_listing(config):
    config.action = "get_listingVersion"
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    body = '{"action": "submit", "note": "submitting new version", "autoApprove": "false"}'
    api_headers['Content-Type'] = 'application/json'
    r = requests.patch(uri, headers=api_headers, data=body)
    del api_headers['Content-Type']
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    if "message" in r_json:
        return r_json["message"]
    else:
        return "this partner has not yet been approved for auto approval. please contact MP admin."

def create_new_listing(config):

    config.action = "get_applications"
    file_name = "/newListing.yaml" if os.path.isfile("/newListing.yaml") else "newListing.yaml"
    with open(file_name, 'r') as stream:
        new_listing_body = yaml.safe_load(stream)
    if 'versionDetails' in new_listing_body:
        vd = new_listing_body['versionDetails']
        config.versionString = vd['versionNumber']
        if 'releaseDate' in vd:
            new_listing_body['versionDetails']['releaseDate'] = str(new_listing_body['versionDetails']['releaseDate'])
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    api_headers['Content-Type'] = 'application/json'
    body = json.dumps(new_listing_body)
    r = requests.post(uri, headers=api_headers, data=body)
    del api_headers['Content-Type']
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["entityId"]

def create_new_package(config, artifactId):
    file_name = "/newPackage.json" if os.path.isfile("/newPackage.json") else "newPackage.json"
    with open(file_name, "r") as file_in:
        body = file_in.read()
    body = body.replace("%%ART_ID%%", artifactId)
    body = body.replace("%%VER%%", config.versionString)
    body = body.replace("%%DESC%%", config.versionString)

    config.action = "get_application_packages"
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    payload = {'json': (None, body)}
    r = requests.post(uri, headers=api_headers, files=payload)
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["message"]

def upload_icon(config):
    config.action = "upload_icon"
    bind_action_dic(config)
    apicall = action_api_uri_dic[config.action]
    uri = api_url + apicall
    file_name = "/icon.png" if os.path.isfile("/icon.png") else "icon.png"
    files = {'image': open(file_name, 'rb')}
    r = requests.post(uri, headers=api_headers, files=files)
    if r.status_code > 299:
        print(r.text)
    r_json = json.loads(r.text)
    return r_json["entityId"]

