import time
import copy
import logging
import string
import random
import base64
from kubernetes import client
from kubernetes.client.rest import ApiException
LOGGER = logging.getLogger()


def set_namespace_value(namespace_name):
    """
    Make namespace as global to be used in later functions

    Args:
        param1: namespace_name - namespace name

    Returns:
       None

    Raises:
        None

    """
    global namespace_value
    namespace_value = namespace_name


def create_custom_object(custom_object_body, stateful_set_not_created):
    """
    Create custom object and waits until stateful sets are created.

    Args:
       param1: custom_object_body - custom object body
       param2: stateful_set_not_created - for operator testcases

    Returns:
       None

    Raises:
        Raises an exception on kubernetes client api failure and asserts

    """
    custom_object_api_instance = client.CustomObjectsApi()
    try:
        custom_object_api_response = custom_object_api_instance.create_namespaced_custom_object(
            group="csi.ibm.com",
            version="v1",
            namespace=namespace_value,
            plural="csiscaleoperators",
            body=custom_object_body,
            pretty=True
        )
        LOGGER.debug(custom_object_api_response)
        LOGGER.info("SpectrumScale CSI custom object created")
    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CustomObjectsApi->create_namespaced_custom_object: {e}")
        assert False

    num = 0
    while (num < 30):
        read_statefulset_api_instance = client.AppsV1Api()
        try:
            read_statefulset_api_response = read_statefulset_api_instance.read_namespaced_stateful_set(
                name="ibm-spectrum-scale-csi-attacher", namespace=namespace_value, pretty=True)
            LOGGER.debug(str(read_statefulset_api_response))
            LOGGER.info("waiting for statefulsets")
            ready_replicas = read_statefulset_api_response.status.ready_replicas
            replicas = read_statefulset_api_response.status.replicas
            if ready_replicas == replicas:
                if stateful_set_not_created is True:
                    LOGGER.error("Statefulsets should not have been created")
                    assert False
                else:
                    return
            num = num + 1
            time.sleep(20)
        except ApiException:
            LOGGER.info("waiting for statefulsets")
            num = num+1
            time.sleep(20)

    if stateful_set_not_created is True:
        LOGGER.info("Expected Failure ,testcase is passed")
        return
    LOGGER.error("problem while creating custom object, (statefulsets are not created)")
    assert False


def delete_custom_object():
    """
    delete custom object  ( csiscaleoperator )

    Args:
       None

    Returns:
       None

    Raises:
        Raises an exception on kubernetes client api failure and asserts

    """
    delete_co_api_instance = client.CustomObjectsApi()
    delete_co_body = client.V1DeleteOptions()

    try:
        delete_co_api_response = delete_co_api_instance.delete_namespaced_custom_object(
            group="csi.ibm.com",
            version="v1",
            namespace=namespace_value,
            plural="csiscaleoperators",
            body=delete_co_body,
            grace_period_seconds=0,
            name="ibm-spectrum-scale-csi")
        LOGGER.debug(str(delete_co_api_response))
    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CustomObjectsApi->delete_namespaced_custom_object: {e}")
        assert False


def check_scaleoperatorobject_is_deleted():
    """
    check  csiscaleoperator deleted or not
    if csiscaleoperator not deleted in 300 seconds , asserts
    """
    count = 30
    list_co_api_instance = client.CustomObjectsApi()
    while (count > 0):
        try:
            list_co_api_response = list_co_api_instance.get_namespaced_custom_object(group="csi.ibm.com",
                                                                                     version="v1",
                                                                                     namespace=namespace_value,
                                                                                     plural="csiscaleoperators",
                                                                                     name="ibm-spectrum-scale-csi"
                                                                                     )
            LOGGER.info("Waiting for custom object deletion")
            LOGGER.debug(str(list_co_api_response))
            count = count-1
            time.sleep(20)
        except ApiException:
            LOGGER.info("SpectrumScale CSI custom object has been deleted")
            return

    LOGGER.error("SpectrumScale CSI custom object is not deleted")
    assert False


def check_scaleoperatorobject_is_deployed(csiscaleoperator_name="ibm-spectrum-scale-csi"):
    """
    Checks csiscaleoperator exists or not

    Args:
       None

    Returns:
       return True  , if csiscaleoperator exists
       return False , if csiscaleoperator does not exist

    Raises:
        None

    """
    read_co_api_instance = client.CustomObjectsApi()
    try:
        read_co_api_response = read_co_api_instance.get_namespaced_custom_object(group="csi.ibm.com",
                                                                                 version="v1",
                                                                                 namespace=namespace_value,
                                                                                 plural="csiscaleoperators",
                                                                                 name=csiscaleoperator_name
                                                                                 )
        LOGGER.debug(str(read_co_api_response))
        LOGGER.info("SpectrumScale CSI custom object exists")
        return True
    except ApiException:
        LOGGER.info("SpectrumScale CSI custom object does not exist")
        return False


def check_scaleoperatorobject_statefulsets_state(stateful_name):
    """
    Checks statefulset exists or not
    if not exists , It asserts
    if exists :
        Checks statfulset is up or not
        if statefulsets not up in 120 seconds , it asserts

    Args:
       param1: stateful_name - statefulset name to check

    Returns:
       None

    Raises:
        Raises an exception on kubernetes client api failure.

    """
    read_statefulsets_api_instance = client.AppsV1Api()
    num = 0
    while (num < 124):
        try:
            read_statefulsets_api_response = read_statefulsets_api_instance.read_namespaced_stateful_set(
                name=stateful_name, namespace=namespace_value, pretty=True)
            LOGGER.debug(read_statefulsets_api_response)
            ready_replicas = read_statefulsets_api_response.status.ready_replicas
            replicas = read_statefulsets_api_response.status.replicas
            if ready_replicas == replicas:
                LOGGER.info(f"CSI driver statefulset {stateful_name} is up")
                return
            num += 1
            time.sleep(5)
        except ApiException:
            num += 1
            time.sleep(5)
    LOGGER.info(f"CSI driver statefulset {stateful_name} does not exist")
    assert False


def check_scaleoperatorobject_daemonsets_state(csiscaleoperator_name="ibm-spectrum-scale-csi"):
    """
    Checks daemonset exists or not
    If not exists , It asserts
    if exists :
        Checks daemonset is running or not
        if not running , It asserts

    Args:
       None

    Returns:
       returns True, desired_number_scheduled , if daemonset pods are running
       returns False, desired_number_scheduled , if daemonset pods are not running

    Raises:
        Raises an exception on kubernetes client api failure.

    """
    read_daemonsets_api_instance = client.AppsV1Api()
    num = 0
    while (num < 30):
        try:
            read_daemonsets_api_response = read_daemonsets_api_instance.read_namespaced_daemon_set(
                name=csiscaleoperator_name, namespace=namespace_value, pretty=True)
            LOGGER.debug(read_daemonsets_api_response)
            current_number_scheduled = read_daemonsets_api_response.status.current_number_scheduled
            desired_number_scheduled = read_daemonsets_api_response.status.desired_number_scheduled
            number_available = read_daemonsets_api_response.status.number_available
            if number_available == current_number_scheduled == desired_number_scheduled:
                LOGGER.info("CSI driver daemonset ibm-spectrum-scale-csi's pods are Running")
                return True, desired_number_scheduled

            time.sleep(20)
            num += 1
            LOGGER.info("waiting for daemonsets")
        except ApiException:
            time.sleep(20)
            num += 1
            LOGGER.info("waiting for daemonsets")

    LOGGER.error(
        "Expected CSI driver daemonset ibm-spectrum-scale-csi's pods are not Running")
    return False, desired_number_scheduled


def create_secret(secret_data_passed, secret_name):
    """
    Create secret secet_name

    Args:
        param1: secret_data_passed - data for secret body
        param2: secret_name - name of secret to be created

    Returns:
        None

    Raises:
        Raises an exception on kubernetes client api failure and asserts

    """
    secret_api_instance = client.CoreV1Api()
    secret_data = copy.deepcopy(secret_data_passed)
    secret_data["username"] = base64encoder(secret_data["username"])
    secret_data["password"] = base64encoder(secret_data["password"])
    secret_metadata = client.V1ObjectMeta(
        name=secret_name,
        labels={"product": "ibm-spectrum-scale-csi"}
    )
    secret_body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=secret_metadata,
        data=secret_data
    )
    try:
        LOGGER.info(f'Creating secret {secret_name}')
        secret_api_response = secret_api_instance.create_namespaced_secret(
            namespace=namespace_value,
            body=secret_body,
            pretty=True
        )
        LOGGER.debug(str(secret_api_response))
    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CoreV1Api->create_namespaced_secret: {e}")
        assert False


def delete_secret(secret_name):
    """
    delete secret secret_name

    Args:
       param1: secret_name - name of secret to be deleted

    Returns:
       None

    Raises:
        Raises an exception on kubernetes client api failure and asserts

    """

    delete_secret_api_instance = client.CoreV1Api()
    try:
        delete_secret_api_response = delete_secret_api_instance.delete_namespaced_secret(
            name=secret_name, namespace=namespace_value, pretty=True)
        LOGGER.info(f'Secret {secret_name} has been deleted')
        LOGGER.debug(str(delete_secret_api_response))
    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CoreV1Api->delete_namespaced_secret: {e}")
        assert False


def check_secret_exists(secret_name):
    """
    Checks secret secret_name exists or not

    Args:
       param1: secret_name - name of secret to be checked

    Returns:
       return True  , if secret exists
       return False , if secret does not exist

    Raises:
        None

    """

    api_instance = client.CoreV1Api()
    try:
        api_response = api_instance.read_namespaced_secret(
            name=secret_name, namespace=namespace_value, pretty=True)
        LOGGER.debug(str(api_response))
        LOGGER.info(f'Secret {secret_name} exists')
        return True
    except ApiException:
        LOGGER.info(f'Secret {secret_name} does not exist')
        return False


def check_secret_is_deleted(secret_name):
    """
    checks secret deleted or not
    if secret not deleted in 120 seconds , asserts

    Args:
       param1: secret_name - name of secret to be checked
    """
    var = True
    count = 12
    api_instance = client.CoreV1Api()
    while (var and count > 0):
        try:
            api_response = api_instance.read_namespaced_secret(
                name=secret_name, namespace=namespace_value, pretty=True)
            LOGGER.info("still deleting secret")
            LOGGER.debug(str(api_response))
            count = count-1
            time.sleep(10)
        except ApiException:
            LOGGER.info(f"Secret {secret_name} has been deleted")
            var = False

    if count <= 0:
        LOGGER.error(f"Secret {secret_name} is not deleted")
        assert False


def create_configmap(file_path, make_cacert_wrong, configmap_name):
    """
    Create configmap with file at file_path
    if make_cacert_wrong==True then it makes cacert wrong

    Args:
        param1: file_path - path of cacert file
        param2: make_cacert_wrong - for operator testcase, cacert wrong

    Returns:
       None

    Raises:
        Raises an exception on kubernetes client api failure and asserts

    """
    api_instance = client.CoreV1Api()
    metadata = client.V1ObjectMeta(
        name=configmap_name,
        namespace=namespace_value,
    )
    with open(file_path, 'r') as f:
        file_content = f.read()
    if make_cacert_wrong:
        file_content = file_content[0:50]+file_content[-50:-1]
    data_dict = {}
    data_dict[configmap_name] = file_content
    configmap = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        data=data_dict,
        metadata=metadata
    )
    try:
        api_response = api_instance.create_namespaced_config_map(
            namespace=namespace_value,
            body=configmap,
            pretty=True,
        )
        LOGGER.debug(str(api_response))
        LOGGER.info(f"configmap {configmap_name} has been created")

    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CoreV1Api->create_namespaced_config_map: {e}")
        assert False


def delete_configmap(configmap_name):
    """
    deletes configmap

    Args:
       None

    Returns:
       None

    Raises:
        Raises an exception on kubernetes client api failure and asserts

    """
    api_instance = client.CoreV1Api()
    try:
        api_response = api_instance.delete_namespaced_config_map(
            namespace=namespace_value,
            name=configmap_name,
            pretty=True,
        )
        LOGGER.debug(str(api_response))
        LOGGER.info(f"configmap {configmap_name} has been deleted")

    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CoreV1Api->create_namespaced_config_map: {e}")
        assert False


def check_configmap_exists(configmap_name):
    """
    Checks configmap configmap_name exists or not

    Args:
       param1: configmap_name - name of configmap to be checked

    Returns:
       return True  , if configmap exists
       return False , if configmap does not exist

    Raises:
        None

    """

    api_instance = client.CoreV1Api()
    try:
        api_response = api_instance.read_namespaced_config_map(
            namespace=namespace_value,
            name=configmap_name,
            pretty=True,
        )
        LOGGER.debug(str(api_response))
        LOGGER.info(f'configmap {configmap_name} exists')
        return True
    except ApiException:
        LOGGER.info(f'configmap {configmap_name} does not exist')
        return False


def check_configmap_is_deleted(configmap_name):
    """
    checks configmap deleted or not
    if configmap not deleted in 120 seconds , asserts

    Args:
       param1: configmap_name - name of configmap to be checked
    """
    count = 12
    api_instance = client.CoreV1Api()
    while (count > 0):
        try:
            api_response = api_instance.read_namespaced_config_map(
                namespace=namespace_value,
                name=configmap_name,
                pretty=True,
            )
            LOGGER.info("still deleting configmap")
            LOGGER.debug(str(api_response))
            count = count-1
            time.sleep(10)
        except ApiException:
            LOGGER.info(f"configmap {configmap_name} deletion confirmed")
            return

    LOGGER.error(f"configmap {configmap_name} is not deleted")
    assert False


def randomStringDigits(stringLength=6):
    """Generate a random string of letters and digits """
    lettersAndDigits = string.ascii_letters + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))


def base64encoder(input_str):
    """Takes input string and converts it to base 64 string"""
    message_bytes = input_str.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')
    return base64_message


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def check_pod_running(pod_name):
    """
    checking phase of pod pod_name to be running
    if not running then asserts
    """

    api_instance = client.CoreV1Api()
    val = 0
    while val < 12:
        try:
            api_response = api_instance.read_namespaced_pod(
                name=pod_name, namespace=namespace_value, pretty=True)
            LOGGER.debug(str(api_response))
            if api_response.status.phase == "Running":
                LOGGER.info(f'POD Check : POD {pod_name} is Running')
                return
            time.sleep(5)
            val += 1
        except ApiException as e:
            LOGGER.error(
                f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")
            LOGGER.info(f"POD Check : POD {pod_name} does not exists on Cluster")
            assert False
    LOGGER.error(f'POD Check : POD {pod_name} is not Running')
    assert False


def get_driver_ds_pod_name():
    try:
        pod_list_api_instance = client.CoreV1Api()
        pod_list_api_response = pod_list_api_instance.list_namespaced_pod(
            namespace=namespace_value, pretty=True, field_selector="spec.serviceAccountName=ibm-spectrum-scale-csi-node")
        demonset_pod_name = pod_list_api_response.items[0].metadata.name
        LOGGER.debug(str(pod_list_api_response))
        return demonset_pod_name
    except ApiException as e:
        LOGGER.error(
            f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")
        assert False


def get_driver_image():
    pod_name = get_driver_ds_pod_name()
    api_instance = client.CoreV1Api()
    try:
        api_response = api_instance.read_namespaced_pod(
            name=pod_name, namespace=namespace_value, pretty=True)
        for container in api_response.status.container_statuses:
            if(container.name == "ibm-spectrum-scale-csi"):
                LOGGER.info(f"CSI driver image :  {container.image}")
                LOGGER.info(f"CSI driver image id : {container.image_id}")
    except ApiException:
        LOGGER.info("Unable to get driver image")


def get_scaleoperatorobject_values(namespace_value, csiscaleoperator_name="ibm-spectrum-scale-csi"):
    read_cr_api_instance = client.CustomObjectsApi()
    try:
        read_cr_api_response = read_cr_api_instance.get_namespaced_custom_object(group="csi.ibm.com",
                                                                                 version="v1", namespace=namespace_value, plural="csiscaleoperators", name=csiscaleoperator_name)
        LOGGER.debug(str(read_cr_api_response))
        return read_cr_api_response
    except ApiException:
        return False
