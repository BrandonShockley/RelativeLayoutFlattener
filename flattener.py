import xml.etree.ElementTree as ET
import sys
from enum import Enum, auto

if (len(sys.argv) < 2):
    print("ERROR: Please provide a path to the xml file containing the RelativeLayout")
    exit()

#Read the xml file into memory
ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
xml_tree = ET.parse(sys.argv[1])
xml_root = xml_tree.getroot()

#Get the horizontal scale factor if there is one
scale = 1.0
if (len(sys.argv) >= 3):
    scale = float(sys.argv[2])

#Check that the root is a relative layout
if (xml_root.tag != "RelativeLayout"):
    print("ERROR: XML File must have RelativeLayout as root")
    exit()

#Make android namespace
ns = {"android" : "http://schemas.android.com/apk/res/android"}

def get(element: ET.Element, key: str, namespace = ns):
    return element.get("{" + namespace["android"] + "}" + key)

def set_attrib(element: ET.Element, key: str, value, namespace = ns):
    element.set("{" + namespace["android"] + "}" + key, value)

#Make the node class that makes up the tree
class Node:

    def __init__(self, name: str, pos=0, size=0):
        self.name = name
        self.size = size
        self.pos = pos
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def destroy_children(self):
        copy = self.children.copy()
        self.children = []
        return copy

    def find_child(self, name: str):
        def find_child_rec(node, name: str):
            #Base case 1: Node is found
            if node.name == name:
                return node
            #Base case 2: No children
            if len(node.children) == 0:
                return None

            #Recursive case: Check all children
            result = None
            for child in node.children:
                result = find_child_rec(child, name)
                if result != None:
                    return result
            return None
        return find_child_rec(self, name)

    def flatten(self):

        def flatten_rec(node):
            for child in node.children:
                #Can't bubble up if child has children
                if len(child.children) > 0:
                    new_children = flatten_rec(child)
                    for new_child in new_children:
                        node.add_child(new_child)

                #Locally globalize the child position (relative to this node's parent)
                child.pos = child.pos + node.pos

            #Kill the children, but pass a copy down the stack
            return node.destroy_children()
        
        self.children = flatten_rec(self)

    def scale_children(self, scale):
        for child in self.children:
            child.pos = int(child.pos * scale)

    def print_children(self):
        def print_children_rec(node, level):
            spaces = ""
            for i in range(level):
                spaces = spaces + "    "
            print(spaces + "Level: " + str(level) + ", ID: " + node.name + ", Pos: " + str(node.pos) + ", Size: " + str(node.size))
            if (len(node.children) > 0):
                print(spaces + "My children:")
            for child in node.children:
                print_children_rec(child, level + 1)
        print_children_rec(self, 0)

#The dummy root nodes
root_x = Node("root_x")
root_y = Node("root_y")

def rmdp(text: str):
    return int(text[:-2])

#Build the tree for the x coordinate
#Strategy: 
# Scan through file and create list of objects
# For each object, see if its parent is in tree 
# Add them as children of parent (and remove from list)
# Repeat until list is empty

objects = []

for child in xml_root:
    objects.append(child)

#Explicitly create top level nodes
objects_copy = objects.copy()
for obj in objects:
    #Get the id and width
    id = get(obj, "id")
    width = rmdp(get(obj, "layout_width"))

    #Get the left margin
    if get(obj, "layout_alignParentLeft") != None:
        pos = get(obj, "layout_marginLeft")
        root_x.add_child(Node(id, rmdp(pos) if pos != None else 0, width))
        print("Added " + id + " as root child")
        #Remove from big list copy
        objects_copy.remove(obj)
    elif get(obj, "layout_alignParentRight") != None or get(obj, "layout_centerHorizontal") != None or get(obj, "layout_centerInParent") != None:
        print("WARNING: "+ id + "isn't aligned with the left of the parent and this thing can't infer the width of a parent")
        exit()
    

#Update big list
objects = objects_copy.copy()

anomolies = []

#Continue algorithm til list is empty
while len(objects) > 0:
    objects_copy = objects.copy()
    print(str(len(objects)) + " objects left")

    for obj in objects:
        #Get the id and width
        id = get(obj, "id")
        width = rmdp(get(obj, "layout_width"))

        #Run through and see which of these alignments applies
        parent = get(obj, "layout_alignLeft")
        if parent != None:
            parent_node = root_x.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginLeft")
                parent_node.add_child(Node(id, rmdp(pos) if pos != None else 0, width))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_alignRight")
        if parent != None:
            parent_node = root_x.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginRight")
                parent_node.add_child(Node(id, parent_node.size - width - (rmdp(pos) if pos != None else 0), width))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_toLeftOf")
        if parent != None:
            parent_node = root_x.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginRight")
                parent_node.add_child(Node(id, -width - (rmdp(pos) if pos != None else 0), width))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_toRightOf")
        if parent != None:
            parent_node = root_x.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginLeft")
                parent_node.add_child(Node(id, parent_node.size + (rmdp(pos) if pos != None else 0), width))
                objects_copy.remove(obj)
            continue
        anomolies.append(id)
        objects_copy.remove(obj)

    objects = objects_copy.copy()

#Done with horizontal scan
print("Done with horizontal scan")

if len(anomolies) > 0:
    print("Anomolies found: " + str(anomolies))
root_x.print_children()

#Now gotta flatten the tree
root_x.flatten()

#Scale it
root_x.scale_children(scale)

root_x.print_children()

#--------------------------------------------------- Same thing for vertical ----------------------------------------------#
objects = []

for child in xml_root:
    objects.append(child)

#Explicitly create top level nodes
objects_copy = objects.copy()
for obj in objects:
    #Get the id and width
    id = get(obj, "id")
    height = rmdp(get(obj, "layout_height"))

    #Get the left margin
    if get(obj, "layout_alignParentTop") != None:
        pos = get(obj, "layout_marginTop")
        root_y.add_child(Node(id, rmdp(pos) if pos != None else 0, height))
        print("Added " + id + " as root child")
        #Remove from big list copy
        objects_copy.remove(obj)
    elif get(obj, "layout_alignParentBottom") != None or get(obj, "layout_centerVertical") != None or get(obj, "layout_centerInParent") != None:
        print("WARNING: "+ id + "isn't aligned with the top of the parent and this thing can't infer the height of a parent")
        exit()
    

#Update big list
objects = objects_copy.copy()

anomolies = []

#Continue algorithm til list is empty
while len(objects) > 0:
    objects_copy = objects.copy()
    print(str(len(objects)) + " objects left")

    for obj in objects:
        #Get the id and width
        id = get(obj, "id")
        height = rmdp(get(obj, "layout_height"))

        #Run through and see which of these alignments applies
        #Check for the sandwhich case first
        parent = get(obj, "layout_alignTop")
        if parent != None and get(obj, "layout_alignBottom") != None:
            if parent != get(obj, "layout_alignBottom"):
                print("Crap, there's a sandwhich between two distinct things: " + parent + get(obj, "layout_alignBottom"))
                exit()
            else:
                parent_node = root_y.find_child(parent)
                if parent_node != None:
                    pos = get(obj, "layout_marginTop")
                    height = parent_node.size - rmdp(pos) if pos != None else 0
                    parent_node.add_child(Node(id, rmdp(pos) if pos != None else 0, height))
                    objects_copy.remove(obj)
                continue
        parent = get(obj, "layout_alignTop")
        if parent != None:
            parent_node = root_y.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginTop")
                parent_node.add_child(Node(id, rmdp(pos) if pos != None else 0, height))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_alignBaseline")
        if parent != None:
            parent_node = root_y.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginBottom")
                parent_node.add_child(Node(id, parent_node.size // 2 - height // 2 - (rmdp(pos) if pos != None else 0) + 3 * height // 70, height))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_alignBottom")
        if parent != None:
            parent_node = root_y.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginBottom")
                parent_node.add_child(Node(id, parent_node.size - height - (rmdp(pos) if pos != None else 0), height))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_above")
        if parent != None:
            parent_node = root_y.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginBottom")
                parent_node.add_child(Node(id, -height - (rmdp(pos) if pos != None else 0), height))
                objects_copy.remove(obj)
            continue
        parent = get(obj, "layout_below")
        if parent != None:
            parent_node = root_y.find_child(parent)
            if parent_node != None:
                pos = get(obj, "layout_marginTop")
                parent_node.add_child(Node(id, parent_node.size + (rmdp(pos) if pos != None else 0), height))
                objects_copy.remove(obj)
            continue
        anomolies.append(id)
        objects_copy.remove(obj)

    objects = objects_copy.copy()

#Done with horizontal scan
print("Done with vertical scan")

if len(anomolies) > 0:
    print("Anomolies found: " + str(anomolies))
root_y.print_children()

#Now gotta flatten the tree
root_y.flatten()

root_y.print_children()



#------------------------------------ Now we change the XML ------------------------------------------#
entries_to_remove = ["layout_alignTop", "layout_alignBottom",\
                     "layout_above", "layout_below",\
                     "layout_alignBaseline", "layout_alignEnd",\
                     "layout_alignLeft", "layout_alignRight",\
                     "layout_alignStart", "layout_toEndOf",\
                     "layout_toLeftOf", "layout_toRightOf",\
                     "layout_toStartOf", "layout_marginRight",\
                     "layout_marginBottom", "layout_marginEnd"]
for child in xml_root:
    id = get(child, "id")
    #Remove stuff we don't need
    for entry in entries_to_remove:
        str(child.attrib.pop("{" + ns["android"] + "}" + entry, None))

    for node in root_x.children:
        if node.name == id:
            #Add the absolute positioning
            set_attrib(child, "layout_alignParentLeft", "true")
            set_attrib(child, "layout_alignParentStart", "true")
            set_attrib(child, "layout_marginStart", str(node.pos) + "dp")
            set_attrib(child, "layout_marginLeft", str(node.pos) + "dp")
            set_attrib(child, "layout_width", str(node.size) + "dp")
            root_x.children.remove(node)
            break

    for node in root_y.children:
        if node.name == id:
            #Add the absolute positioning
            set_attrib(child, "layout_alignParentTop", "true")
            set_attrib(child, "layout_marginTop", str(node.pos) + "dp")
            set_attrib(child, "layout_height", str(node.size) + "dp")
            root_y.children.remove(node)
            break
    
xml_tree.write(sys.argv[1][:-4] + "_flat" + sys.argv[1][-4:])