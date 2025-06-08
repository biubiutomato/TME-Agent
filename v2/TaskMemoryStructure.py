class TaskNode:
    def __init__(self, slot, value, parent=None, dependencies=None, user_response=None, ai_response=None):
        self.slot = slot  # Identifier for the task or subtask
        self.value = value  # Task content or associated data
        self.parent = parent  # Parent slot name (if any)
        self.dependencies = dependencies or []  # List of dependent slot names
        self.user_response = user_response  # Raw user input associated with this node
        self.ai_response = ai_response  # AI-generated response tied to this node
        self.history = []  # Historical values or updates to this node

    def update_value(self, new_value):
        self.history.append(self.value)
        self.value = new_value

    def __repr__(self):
        return f"<{self.slot}: {self.value} | History: {self.history}>"

class TaskMemoryTree:
    def __init__(self):
        self.nodes = []
        self.root = None  # ✅ Automatically tracks the first root-level task

    def add_node(self, node):
        self.nodes.append(node)
        if node.parent is None and self.root is None:
            self.root = node  # ✅ Set the first node without a parent as the root

    def find_node_by_slot(self, slot):
        return next((n for n in self.nodes if n.slot == slot), None)

    def get_all_slots(self):
        return [n.slot for n in self.nodes]
    
    def replace_slot_and_propagate(self, old_slot, new_slot, new_value):
        """
        Replaces a node's slot and value, and propagates the changes to dependent nodes and parent references.
        """
        node = self.find_node_by_slot(old_slot)
        if node:
            node.history.append((node.slot, node.value))
            node.slot = new_slot
            node.value = new_value
            node.replaced_by = new_slot
            print(f"🔁 {old_slot} → {new_slot}")

            # ✅ Step 1: Update all downstream nodes that depend on this slot
            downstream = [n for n in self.nodes if old_slot in n.dependencies]
            for d in downstream:
                d.dependencies = [
                    new_slot if dep == old_slot else dep for dep in d.dependencies
                ]
                d.ai_response = f"⚠️ Note: '{old_slot}' was replaced with '{new_slot}'"
                print(f"🧠 Updated {d.slot}: dependency → {d.dependencies}")

            # ✅ Step 2: Update parent node's dependencies if it explicitly lists this as a subtask
            parent = self.find_node_by_slot(node.parent)
            if parent and old_slot in parent.dependencies:
                parent.dependencies = [
                    new_slot if dep == old_slot else dep for dep in parent.dependencies
                ]
                print(f"🔧 Updated parent {parent.slot}: dependency → {parent.dependencies}")

def replace_value(memory_nodes, old_value, new_value):
    """
    Replaces values in nodes and tracks replacements in history.
    """
    updated_nodes = []
    for node in memory_nodes:
        if node.value == old_value:
            node.replaced_by = new_value
            node.history.append(f"Replaced {old_value} -> {new_value}")
            node.value = new_value
            updated_nodes.append(node)
    return updated_nodes
