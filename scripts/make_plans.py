"""Build the three standalone JMX plans with one definition of the business flow."""
import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DAY = datetime.date.today().strftime("%Y%m%d")


def prop(node, key, value, tag="stringProp"):
    field = ET.SubElement(node, tag, name=key)
    field.text = str(value)
    return field


def element(tree, tag, label, gui):
    item = ET.SubElement(tree, tag, guiclass=gui, testclass=tag, testname=label, enabled="true")
    return item, ET.SubElement(tree, "hashTree")


def script(tree, kind, label, code):
    item, _ = element(tree, kind, label, "TestBeanGUI")
    prop(item, "scriptLanguage", "groovy")
    prop(item, "cacheKey", "true")
    prop(item, "script", code.strip())


def request(tree, label, method, path, check, body=None, pause=False):
    item, children = element(tree, "HTTPSamplerProxy", label, "HttpTestSampleGui")
    arguments = ET.SubElement(item, "elementProp", name="HTTPsampler.Arguments", elementType="Arguments")
    args = ET.SubElement(arguments, "collectionProp", name="Arguments.arguments")
    if body:
        arg = ET.SubElement(args, "elementProp", name="", elementType="HTTPArgument")
        prop(arg, "HTTPArgument.always_encode", "false", "boolProp")
        prop(arg, "Argument.value", body)
        prop(arg, "Argument.metadata", "=")
        prop(item, "HTTPSampler.postBodyRaw", "true", "boolProp")
    for key, value in dict(domain="127.0.0.1", port="${__P(port,3000)}", protocol="http",
                           path="/api/"+path, method=method, connect_timeout="5000", response_timeout="15000").items():
        prop(item, "HTTPSampler."+key, value)
    if pause:
        timer, _ = element(children, "UniformRandomTimer", "Admin think time", "UniformRandomTimerGui")
        prop(timer, "ConstantTimer.delay", "1000")
        prop(timer, "RandomTimer.range", "2000")
    # Throwing a Groovy assertion marks this HTTP sample failed in JTL.
    script(children, "JSR223Assertion", "Verify "+label,
           "assert prev.responseCode == '200'\ndef j = new groovy.json.JsonSlurper().parse(prev.responseData)\n"+check)
    return children


def workflow(tree, offset):
    login = request(tree, "Login", "POST", "login",
                    "assert j.user.role == 'admin' && j.token\nvars.put('jwt', j.token)",
                    '{"email":"${email}","password":"${password}"}')
    script(login, "JSR223PreProcessor", "Assign CSV fixture and iteration", """
if (!vars.get('slot')) {
    def lines = new File(props.getProperty('fixture', '../data/admin-fixtures.csv')).readLines('UTF-8')
    def keys = lines[0].split(',', -1)
    def row = lines[ctx.threadNum + OFFSET + 1].split(',', -1)
    assert row.size() == keys.size()
    keys.eachWithIndex { key, i -> vars.put(key, row[i]) }
}
def n = vars.getIteration()
vars.put('price', vars.get(n % 2 == 1 ? 'high' : 'low'))
vars.put('code', 'G4-' + props.getProperty('runId', 'local') + '-' + vars.get('slot') + '-' + n)
""".replace("OFFSET", str(offset)))
    controller, admin = element(tree, "GenericController", "Authenticated operations", "LogicControllerGui")
    hdr, _ = element(admin, "HeaderManager", "Thread JWT", "HeaderPanel")
    headers = ET.SubElement(hdr, "collectionProp", name="HeaderManager.headers")
    h = ET.SubElement(headers, "elementProp", name="", elementType="Header")
    prop(h, "Header.name", "Authorization")
    prop(h, "Header.value", "Bearer ${jwt}")
    for name, path, check in [
        ("Users", "admin/users", "it.email == vars.get('email') && it.role == 'admin'"),
        ("Orders", "admin/orders", "it.id == 9001"),
        ("Products", "products", "it.id.toString() == vars.get('product_id')"),
        ("Categories", "categories", "it.id == 1"),
        ("Coupons", "coupons", "it.code == 'SAVE10'"),
    ]:
        request(admin, "Dashboard_"+name, "GET", path, "assert j instanceof List && j.any { "+check+" }",
                pause=name=="Users")
    request(admin, "CreateCoupon", "POST", "admin/coupons", "assert j.message == 'Coupon created' && j.id > 0",
            '{"code":"${code}","type":"percent","discount_value":10,"min_order_amount":100000,"expired_at":"2099-12-31","max_uses_per_user":1}', True)
    request(admin, "UpdatePrice", "PUT", "products/${product_id}", "assert j.message == 'Product updated'",
            '{"name":"${name}","price":${price},"description":"${description}","imageUrl":"${imageUrl}","category_id":${category_id}}', True)
    request(admin, "VerifyPrice", "GET", "products/${product_id}",
            "assert j.id.toString() == vars.get('product_id') && j.price.toString() == vars.get('price')\nassert j.name == vars.get('name') && j.description == vars.get('description') && j.imageUrl == vars.get('imageUrl') && j.category_id.toString() == vars.get('category_id')")
    request(admin, "Orders_AfterPriceUpdate", "GET", "admin/orders", "assert j instanceof List && j.any { it.id == 9001 }", pause=True)


def build(scenario, groups, listener):
    root = ET.Element("jmeterTestPlan", version="1.2", properties="5.0", jmeter="5.6.3")
    name = f"23120207_{scenario}_{DAY}"
    plan, tree = element(ET.SubElement(root, "hashTree"), "TestPlan", name, "TestPlanGui")
    hdr, _ = element(tree, "HeaderManager", "JSON requests", "HeaderPanel")
    headers = ET.SubElement(hdr, "collectionProp", name="HeaderManager.headers")
    h = ET.SubElement(headers, "elementProp", name="", elementType="Header")
    prop(h, "Header.name", "Content-Type")
    prop(h, "Header.value", "application/json")
    offset = 0
    for i, (users, ramp, delay, duration) in enumerate(groups):
        group, subtree = element(tree, "ThreadGroup", f"{scenario}-{i+1}", "ThreadGroupGui")
        prop(group, "ThreadGroup.on_sample_error", "startnextloop")
        loop = ET.SubElement(group, "elementProp", name="ThreadGroup.main_controller", elementType="LoopController", guiclass="LoopControlPanel", testclass="LoopController", testname="Loop Controller", enabled="true")
        prop(loop, "LoopController.continue_forever", "false", "boolProp")
        prop(loop, "LoopController.loops", "${__P(loops,-1)}")
        for key, val in dict(num_threads=users, ramp_time=ramp, delay=delay, duration=duration).items():
            prop(group, "ThreadGroup."+key, val)
        prop(group, "ThreadGroup.scheduler", "true", "boolProp")
        workflow(subtree, offset)
        offset += users if isinstance(users, int) else 0
    item, _ = element(tree, "ResultCollector", listener[0], listener[1])
    item.set("enabled", "false")
    ET.indent(root)
    ET.ElementTree(root).write(ROOT/"plans"/(name+".jmx"), encoding="utf-8", xml_declaration=True)


build("Load", [("${__P(vu,10)}", "${__P(ramp,60)}", 0, "${__P(duration,360)}")], ("Summary Report", "SummaryReport"))
build("Stress", [(10,30,0,600),(10,30,150,450),(20,30,300,300),(40,30,450,150)], ("Aggregate Report", "StatVisualizer"))
build("Spike", [(5,1,0,365),(45,5,120,65)], ("Response Time Graph", "RespTimeGraphVisualizer"))
