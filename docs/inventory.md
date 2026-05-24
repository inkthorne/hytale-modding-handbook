# Inventory API

**Doc type:** Java API · **Verified against build-12**

The inventory system lets plugins read and mutate player inventories — moving, adding, removing, sorting, and filtering item stacks across the hotbar, storage, armor, utility, tools, and backpack sections.

## Overview

Implemented in `com.hypixel.hytale.server.core.inventory` and provides:
- A sectioned player `Inventory` (hotbar, storage, armor, utility, tools, backpack) with combined views
- `ItemStack` value type with metadata, plus the `Item` config that backs each stack
- `ItemContainer` operations: add, remove, move, smart-move, quick-stack, sort, and filter
- Slot filtering (`SlotFilter`, `FilterType`, `FilterActionType`) and sorting (`SortType`)
- A transaction layer (`ItemStackTransaction`, `MoveTransaction`, `ListTransaction`) for atomic, reversible edits
- Crafting (`CraftingRecipe`, `BenchRequirement`) and ECS inventory/crafting events

## Architecture
```
Inventory  (player; sectioned)
├── Sections → ItemContainer
│   ├── getHotbar / getStorage / getArmor / getUtility / getTools / getBackpack
│   └── CombinedItemContainer  (cross-section views)
├── ItemContainer implementations
│   ├── SimpleItemContainer
│   └── CombinedItemContainer
├── ItemStack  (backed by Item config)
├── Filtering & Sorting
│   ├── SlotFilter (FilterType / FilterActionType)
│   └── SortType
├── Transaction System
│   ├── ItemStackTransaction / MoveTransaction
│   ├── ListTransaction
│   └── ActionType
├── Crafting
│   ├── CraftingRecipe
│   └── BenchRequirement / BenchType
└── Events (ECS)
    ├── InventoryChangeEvent / DropItemEvent
    ├── InteractivelyPickupItemEvent / SwitchActiveSlotEvent
    └── CraftRecipeEvent (Pre / Post)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Inventory` | `server.core.inventory` | Player inventory with multiple sections |
| `ItemStack` | `server.core.inventory` | A stack of items with count and metadata |
| `Item` | `server.core.asset.type.item.config` | Item definition/config backing an `ItemStack` |
| `ItemContainer` | `server.core.inventory.container` | A container of slots; add/remove/move/filter API |
| `ItemContainer.ItemContainerChangeEvent` | `server.core.inventory.container` | Fired when a container's contents change |
| `SimpleItemContainer` | `server.core.inventory.container` | Basic standalone container implementation |
| `CombinedItemContainer` | `server.core.inventory.container` | View spanning multiple sections as one container |
| `SlotFilter` | `server.core.inventory.container.filter` | Per-slot filtering rules |
| `FilterType` | `server.core.inventory.container.filter` | Filter category enum |
| `FilterActionType` | `server.core.inventory.container.filter` | Allow/deny action enum for filters |
| `SortType` | `server.core.inventory.container` | Container sort ordering enum |
| `SmartMoveType` | `protocol` | Smart-move behavior selector |
| `MaterialQuantity` | `server.core.inventory` | Material-id + quantity pair |
| `ResourceQuantity` | `server.core.inventory` | Resource-type + quantity pair |
| `ItemStackTransaction` | `server.core.inventory.transaction` | Single reversible item-stack edit |
| `MoveTransaction<T>` | `server.core.inventory.transaction` | A move wrapped as a transaction |
| `ListTransaction<T>` | `server.core.inventory.transaction` | Batch of transactions |
| `ActionType` | `server.core.inventory.transaction` | Transaction action kind |
| `CraftingRecipe` | `server.core.asset.type.item.config` | Crafting recipe config (inputs, outputs, requirements) |
| `BenchRequirement` | `protocol` | Required crafting bench for a recipe |
| `BenchType` | `protocol` | Crafting bench type enum |
| `CraftRecipeEvent` | `server.core.event.events.ecs` | ECS event for crafting (`Pre`/`Post`) |
| `InventoryChangeEvent` | `server.core.inventory` | Inventory contents changed |
| `DropItemEvent` | `server.core.event.events.ecs` | Item dropped |
| `InteractivelyPickupItemEvent` | `server.core.event.events.ecs` | Item picked up interactively |
| `SwitchActiveSlotEvent` | `server.core.event.events.ecs` | Active slot changed |

## Inventory
**Package:** `com.hypixel.hytale.server.core.inventory`

Player inventory with multiple sections.

### Section IDs
```java
static final int HOTBAR_SECTION_ID
static final int STORAGE_SECTION_ID
static final int ARMOR_SECTION_ID
static final int UTILITY_SECTION_ID
static final int TOOLS_SECTION_ID
static final int BACKPACK_SECTION_ID
```

### Default Capacities
```java
static final short DEFAULT_HOTBAR_CAPACITY
static final short DEFAULT_UTILITY_CAPACITY
static final short DEFAULT_TOOLS_CAPACITY
static final short DEFAULT_ARMOR_CAPACITY
static final short DEFAULT_STORAGE_ROWS
static final short DEFAULT_STORAGE_COLUMNS
static final short DEFAULT_STORAGE_CAPACITY
static final byte INACTIVE_SLOT_INDEX
```

### Get Sections
```java
ItemContainer getHotbar()
ItemContainer getStorage()
ItemContainer getArmor()
ItemContainer getUtility()
ItemContainer getTools()
ItemContainer getBackpack()
ItemContainer getSectionById(int sectionId)
```

### Combined Containers
```java
CombinedItemContainer getCombinedHotbarFirst()
CombinedItemContainer getCombinedStorageFirst()
CombinedItemContainer getCombinedArmorHotbarUtilityStorage()
CombinedItemContainer getCombinedHotbarUtilityConsumableStorage()
CombinedItemContainer getCombinedBackpackStorageHotbar()
CombinedItemContainer getCombinedBackpackStorageHotbarFirst()
CombinedItemContainer getCombinedStorageHotbarBackpack()
```

### Active Slots
```java
// Hotbar
byte getActiveHotbarSlot()
void setActiveHotbarSlot(Ref<EntityStore> ref, byte slot, ComponentAccessor<EntityStore> accessor)
ItemStack getActiveHotbarItem()

// Tools
byte getActiveToolsSlot()
void setActiveToolsSlot(Ref<EntityStore> ref, byte slot, ComponentAccessor<EntityStore> accessor)
ItemStack getToolsItem()
ItemStack getActiveToolItem()
boolean usingToolsItem()
void setUsingToolsItem(boolean using)

// Utility
byte getActiveUtilitySlot()
void setActiveUtilitySlot(Ref<EntityStore> ref, byte slot, ComponentAccessor<EntityStore> accessor)
void setActiveUtilitySlot(Holder<EntityStore> holder, byte slot)
ItemStack getUtilityItem()

// General
byte getActiveSlot(int sectionId)
void setActiveSlot(Ref<EntityStore> ref, int sectionId, byte slot, ComponentAccessor<EntityStore> accessor)
void setActiveSlot(Holder<EntityStore> holder, int sectionId, byte slot)
ItemStack getItemInHand()
```

### Item Operations
```java
void moveItem(int fromSection, int fromSlot, int toSection, int toSlot, int count)
void smartMoveItem(Ref<EntityStore> ref, int section, int slot, int count, SmartMoveType type, PlayerSettings settings, ComponentAccessor<EntityStore> accessor)
ListTransaction<MoveTransaction<ItemStackTransaction>> takeAll(int section, PlayerSettings settings)
ListTransaction<MoveTransaction<ItemStackTransaction>> putAll(int section)
ListTransaction<MoveTransaction<ItemStackTransaction>> quickStack(int section)
List<ItemStack> dropAllItemStacks()
void clear()
```

### Sorting & Management
```java
void sortStorage()
static boolean containsBrokenItem(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)
```

---

## SmartMoveType
**Package:** `com.hypixel.hytale.protocol`

Enum for smart move operations. Used with `Inventory.smartMoveItem()`.

```java
public enum SmartMoveType {
    EquipOrMergeStack,     // Equip item or merge with existing stack
    PutInHotbarOrWindow,   // Move to hotbar or active window
    PutInHotbarOrBackpack  // Move to hotbar or backpack
}
```

---

## ItemStack
**Package:** `com.hypixel.hytale.server.core.inventory`

Represents an item with quantity and metadata. **Immutable** - modification methods return new instances.

### Constants
```java
static final ItemStack EMPTY          // Empty stack constant
static final ItemStack[] EMPTY_ARRAY  // Empty array constant
```

### Constructors
```java
ItemStack(String itemId)
ItemStack(String itemId, int quantity)
ItemStack(String itemId, int quantity, BsonDocument metadata)
ItemStack(String itemId, int quantity, double durability, double maxDurability, BsonDocument metadata)
```

### Item ID Format

Item IDs match the asset filename without the `.json` extension. They do **not** use namespace prefixes.

**Examples:**
- `Weapon_Sword_Wood` (wooden sword)
- `Food_Bread` (bread)
- `Tool_Pickaxe_Iron` (iron pickaxe)

Find valid item IDs in `Assets.zip` under `Assets/Server/Item/Items/`, organized by category.

### Validating Item IDs

To check if an item ID is valid after creating an ItemStack:

```java
ItemStack stack = new ItemStack(itemId, quantity);
if (stack.getItem() == Item.UNKNOWN) {
    // Invalid item ID - handle error
}
```

**Note:** Prefer checking against `Item.UNKNOWN` rather than using `isValid()`, which may reject valid items in some cases.

### Getters
```java
String getItemId()
int getQuantity()
BsonDocument getMetadata()
double getDurability()
double getMaxDurability()
boolean isUnbreakable()
boolean isBroken()
boolean isEmpty()
boolean isValid()
Item getItem()
String getBlockKey()
boolean getOverrideDroppedItemAnimation()
```

### Modification Methods (Return New ItemStack)
```java
// Durability
ItemStack withDurability(double durability)
ItemStack withMaxDurability(double maxDurability)
ItemStack withIncreasedDurability(double amount)
ItemStack withRestoredDurability(double amount)

// State & Quantity
ItemStack withState(String state)
ItemStack withQuantity(int quantity)

// Metadata
ItemStack withMetadata(BsonDocument metadata)
<T> ItemStack withMetadata(KeyedCodec<T> codec, T value)
<T> ItemStack withMetadata(String key, Codec<T> codec, T value)
ItemStack withMetadata(String key, BsonValue value)
```

### Metadata Access
```java
<T> T getFromMetadataOrNull(KeyedCodec<T> codec)
<T> T getFromMetadataOrNull(String key, Codec<T> codec)
<T> T getFromMetadataOrDefault(String key, BuilderCodec<T> codec)
```

### Comparison Methods
```java
boolean isStackableWith(ItemStack other)
boolean isEquivalentType(ItemStack other)

// Static versions
static boolean isEmpty(ItemStack stack)
static boolean isStackableWith(ItemStack a, ItemStack b)
static boolean isEquivalentType(ItemStack a, ItemStack b)
static boolean isSameItemType(ItemStack a, ItemStack b)
```

### Static Factory
```java
static ItemStack fromPacket(ItemQuantity packet)
```

---

## Item
**Package:** `com.hypixel.hytale.server.core.asset.type.item.config`

Asset type for items. Get from `ItemStack.getItem()`.

### Constants
```java
static final Item UNKNOWN  // Unknown/invalid item
```

### Static Methods
```java
static AssetStore<String, Item, ...> getAssetStore()
static AssetMap<String, Item> getAssetMap()
```

### Identity
```java
String getId()
String getBlockId()           // Associated block ID (if placeable)
String getTranslationKey()
String getDescriptionTranslationKey()
boolean hasBlockType()        // Whether item places a block
```

### Properties
```java
int getMaxStack()
int getItemLevel()
int getQualityIndex()
double getMaxDurability()
boolean isConsumable()
boolean isVariant()
boolean isState()
boolean dropsOnDeath()
```

### Visual
```java
String getModel()
String getTexture()
String getIcon()
float getScale()
String getReticleId()
AssetIconProperties getIconProperties()
```

### Equipment Types
```java
ItemTool getTool()            // Tool properties (if tool)
ItemArmor getArmor()          // Armor properties (if armor)
ItemWeapon getWeapon()        // Weapon properties (if weapon)
ItemGlider getGlider()        // Glider properties (if glider)
ItemUtility getUtility()      // Utility properties (if utility item)
```

### Interactions
```java
Map<InteractionType, String> getInteractions()
Map<String, String> getInteractionVars()
InteractionConfiguration getInteractionConfig()
```

### State Management
```java
String getItemIdForState(String state)
Item getItemForState(String state)
String getStateForItem(Item item)
String getStateForItem(String itemId)
```

### Usage Example
```java
ItemStack stack = inventory.getItemInHand();
if (!stack.isEmpty()) {
    Item item = stack.getItem();

    // Check item type
    if (item.getWeapon() != null) {
        playerRef.sendMessage(Message.raw("Holding a weapon!"));
    }

    // Get max stack size
    int maxStack = item.getMaxStack();

    // Check if placeable
    if (item.hasBlockType()) {
        String blockId = item.getBlockId();
    }
}
```

---

## ItemContainer
**Package:** `com.hypixel.hytale.server.core.inventory.container`

Abstract base class for inventory containers with filtering support.

### Capacity
```java
abstract short getCapacity()
ItemStack getItemStack(short slotIndex)
```

### Filtering
```java
abstract void setGlobalFilter(FilterType filterType)
abstract void setSlotFilter(FilterActionType actionType, short slotIndex, SlotFilter filter)
```

### Adding Items
```java
boolean canAddItemStack(ItemStack item)
boolean canAddItemStack(ItemStack item, boolean addAllOrNothing, boolean fullStacks)

ItemStackTransaction addItemStack(ItemStack item)
ItemStackTransaction addItemStack(ItemStack item, boolean addAllOrNothing, boolean fullStacks, boolean filter)
ItemStackTransaction addItemStacks(List<ItemStack> items)
ListTransaction<ItemStackSlotTransaction> addItemStacksOrdered(List<ItemStack> items)
ListTransaction<ItemStackSlotTransaction> addItemStacksOrdered(short startSlot, List<ItemStack> items)
ListTransaction<ItemStackSlotTransaction> addItemStacksOrdered(List<ItemStack> items, boolean addAllOrNothing, boolean fullStacks)
ListTransaction<ItemStackSlotTransaction> addItemStacksOrdered(short startSlot, List<ItemStack> items, boolean addAllOrNothing, boolean fullStacks)
```

### Removing Items
```java
// By slot
SlotTransaction removeItemStackFromSlot(short slotIndex)
ItemStackSlotTransaction removeItemStackFromSlot(short slotIndex, int quantity)
ItemStackSlotTransaction removeItemStackFromSlot(short slotIndex, ItemStack item, int quantity)

// By item
ItemStackTransaction removeItemStack(ItemStack item)
ItemStackTransaction removeItemStacks(List<ItemStack> items)
```

### Removing Materials
```java
MaterialSlotTransaction removeMaterialFromSlot(short slotIndex, MaterialQuantity material)
MaterialTransaction removeMaterial(MaterialQuantity material)
MaterialTransaction removeMaterials(List<MaterialQuantity> materials)
```

### Removing Resources
```java
ResourceSlotTransaction removeResourceFromSlot(short slotIndex, ResourceQuantity resource)
ResourceTransaction removeResource(ResourceQuantity resource)
```

### Moving Items
```java
MoveTransaction<ItemStackTransaction> moveItemStackFromSlot(short slotIndex, ItemContainer destination)
MoveTransaction<SlotTransaction> moveItemStackFromSlotToSlot(short slotIndex, int quantity, ItemContainer destination, short destSlot)
ListTransaction<MoveTransaction<ItemStackTransaction>> moveAllItemStacksTo(ItemContainer... destinations)
ListTransaction<MoveTransaction<ItemStackTransaction>> quickStackTo(ItemContainer... destinations)
ListTransaction<MoveTransaction<SlotTransaction>> combineItemStacksIntoSlot(ItemContainer source, short slotIndex)
ListTransaction<MoveTransaction<SlotTransaction>> swapItems(short slot, ItemContainer container, short containerSlot, short targetSlot)
```

### Utility
```java
ClearTransaction clear()
List<ItemStack> removeAllItemStacks()
List<ItemStack> dropAllItemStacks()
boolean isEmpty()
int countItemStacks(Predicate<ItemStack> filter)
boolean containsItemStacksStackableWith(ItemStack item)
void forEach(ShortObjectConsumer<ItemStack> consumer)
ListTransaction<SlotTransaction> sortItems(SortType sortType)
```

### Events
```java
EventRegistration registerChangeEvent(Consumer<ItemContainerChangeEvent> handler)
EventRegistration registerChangeEvent(EventPriority priority, Consumer<ItemContainerChangeEvent> handler)
EventRegistration registerChangeEvent(short slotIndex, Consumer<ItemContainerChangeEvent> handler)
```

---

## ItemContainer.ItemContainerChangeEvent

**Package:** `com.hypixel.hytale.server.core.inventory.container`

Nested type: `ItemContainer.ItemContainerChangeEvent` (inner class of `ItemContainer`).

Java Record that fires when an item container's contents change. Implements `IEvent<Void>`.

### Record Components

| Method | Return Type | Description |
|--------|-------------|-------------|
| `container()` | `ItemContainer` | The container that changed |
| `transaction()` | `Transaction` | The transaction details |

### Usage Example

Register directly on an ItemContainer:

```java
Player player = store.getComponent(ref, Player.getComponentType());
Inventory inventory = player.getInventory();
ItemContainer hotbar = inventory.getHotbar();

// Listen for changes to this specific container
hotbar.registerChangeEvent(event -> {
    ItemContainer container = event.container();
    Transaction transaction = event.transaction();
    System.out.println("Container changed: " + transaction);
});

// Listen for changes to a specific slot
hotbar.registerChangeEvent((short) 0, event -> {
    System.out.println("First hotbar slot changed!");
});

// With priority
hotbar.registerChangeEvent(EventPriority.EARLY, event -> {
    System.out.println("Early handler for container change");
});
```

### Note

This event is specific to individual `ItemContainer` instances. To listen for general inventory changes across all entities, use `InventoryChangeEvent` instead (see [Inventory Events](#inventory-events)).

> **See also:** [Player Events](player.md#player-events)

---

## SimpleItemContainer
**Package:** `com.hypixel.hytale.server.core.inventory.container`

Thread-safe concrete implementation of ItemContainer.

```java
// Constructor
SimpleItemContainer(short capacity)

// Static factory
static ItemContainer getNewContainer(short capacity)

// Utility methods with drop support
static boolean addOrDropItemStack(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref, ItemContainer container, ItemStack item)
static boolean addOrDropItemStack(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref, ItemContainer container, short startSlot, ItemStack item)
static boolean addOrDropItemStacks(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref, ItemContainer container, List<ItemStack> items)
static boolean tryAddOrderedOrDropItemStacks(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref, ItemContainer container, List<ItemStack> items)
```

---

## CombinedItemContainer
**Package:** `com.hypixel.hytale.server.core.inventory.container`

Combines multiple ItemContainers into a single logical container.

```java
// Constructor
CombinedItemContainer(ItemContainer... containers)

// Access
ItemContainer getContainer(int index)
int getContainersSize()
ItemContainer getContainerForSlot(short slotIndex)
short getCapacity()
CombinedItemContainer clone()
```

---

## SortType
**Package:** `com.hypixel.hytale.server.core.inventory.container`

Enum for sorting options.

```java
public enum SortType {
    NAME,   // Sort alphabetically by item name
    TYPE,   // Sort by item type/category
    RARITY  // Sort by item rarity

    Comparator<ItemStack> getComparator()
}
```

---

## FilterType
**Package:** `com.hypixel.hytale.server.core.inventory.container.filter`

Enum for container-level filtering.

```java
public enum FilterType {
    ALLOW_INPUT_ONLY,   // Only allow items in
    ALLOW_OUTPUT_ONLY,  // Only allow items out
    ALLOW_ALL,          // Allow input and output
    DENY_ALL            // Block all operations

    boolean allowInput()
    boolean allowOutput()
}
```

---

## FilterActionType
**Package:** `com.hypixel.hytale.server.core.inventory.container.filter`

Enum for filter action contexts. Used with `SlotFilter` to determine what operation is being filtered.

```java
public enum FilterActionType {
    ADD,    // Adding item to slot
    REMOVE, // Removing item from slot
    DROP    // Dropping item
}
```

---

## SlotFilter
**Package:** `com.hypixel.hytale.server.core.inventory.container.filter`

Interface for per-slot filtering. Set via `ItemContainer.setSlotFilter()`.

### Constants
```java
static final SlotFilter ALLOW  // Always allow
static final SlotFilter DENY   // Always deny
```

### Methods
```java
// Test if the operation should be allowed
boolean test(FilterActionType actionType, ItemContainer container, short slot, ItemStack item)
```

### Usage Example
```java
ItemContainer hotbar = inventory.getHotbar();

// Deny all operations on slot 0
hotbar.setSlotFilter(FilterActionType.ADD, (short) 0, SlotFilter.DENY);

// Custom filter - only allow weapons in slot 1
hotbar.setSlotFilter(FilterActionType.ADD, (short) 1, (action, container, slot, item) -> {
    return item.getItem().getWeapon() != null;
});
```

---

## MaterialQuantity
**Package:** `com.hypixel.hytale.server.core.inventory`

Represents a quantity of crafting material.

### Fields
```java
String itemId
String resourceTypeId
String tag
int tagIndex
int quantity
BsonDocument metadata
```

### Methods
```java
ItemStack toItemStack()
ResourceQuantity toResource()
MaterialQuantity clone(int newQuantity)
```

---

## ResourceQuantity
**Package:** `com.hypixel.hytale.server.core.inventory`

Represents a quantity of a resource.

### Fields
```java
String resourceId
int quantity
```

### Methods
```java
String getResourceId()
int getQuantity()
ResourceQuantity clone(int newQuantity)
ItemResourceType getResourceType(Item item)
```

---

## Transaction System

All item operations return Transaction objects indicating success/failure.

### ActionType
**Package:** `com.hypixel.hytale.server.core.inventory.transaction`

Enum for transaction operation types. Get via `ItemStackTransaction.getAction()`.

```java
public enum ActionType {
    SET,     // Set slot to specific item
    ADD,     // Add item to container
    REMOVE,  // Remove item from container
    REPLACE  // Replace existing item

    boolean isAdd()
    boolean isRemove()
    boolean isDestroy()
}
```

### ItemStackTransaction
```java
boolean succeeded()
boolean wasSlotModified(short slotIndex)
ActionType getAction()              // Operation type
ItemStack getQuery()                // Original item query
ItemStack getRemainder()            // Leftover items not processed
boolean isAllOrNothing()
boolean isFilter()                  // Whether filtering blocked operation
List<ItemStackSlotTransaction> getSlotTransactions()
```

#### Transaction Result Patterns

**Basic success check:**
```java
ItemStack item = new ItemStack("Weapon_Sword_Wood", 1);
ItemStackTransaction result = container.addItemStack(item);

if (result.succeeded()) {
    // Item was fully added
} else {
    // Operation failed or partially completed
}
```

**Handling partial additions (inventory full):**
```java
ItemStack itemStack = new ItemStack("Food_Bread", 10);
CombinedItemContainer combined = inventory.getCombinedHotbarFirst();

ItemStackTransaction result = combined.addItemStack(itemStack);
ItemStack remainder = result.getRemainder();

// Calculate how many were actually added
int requestedQuantity = itemStack.getQuantity();
int remainderQuantity = (remainder != null && !remainder.isEmpty())
    ? remainder.getQuantity()
    : 0;
int addedQuantity = requestedQuantity - remainderQuantity;

if (addedQuantity == requestedQuantity) {
    // All items added successfully
    playerRef.sendMessage(Message.raw("Added " + addedQuantity + " items"));
} else if (addedQuantity > 0) {
    // Partial success - inventory was full
    playerRef.sendMessage(Message.raw(
        "Added " + addedQuantity + " items. " + remainderQuantity + " did not fit."
    ));
} else {
    // No items added - inventory completely full
    playerRef.sendMessage(Message.raw("Inventory is full!"));
}
```

**Complete give item pattern:**

Full working example: [`examples/inventory/.../GiveCommand.java`](../examples/inventory/src/main/java/hytale/examples/inventory/GiveCommand.java) (compiles against the build-12 jar).

```java
public void giveItem(PlayerRef playerRef, Player player, String itemId, int quantity) {
    ItemStack itemStack = new ItemStack(itemId, quantity);

    // Validate item exists
    if (itemStack.getItem() == Item.UNKNOWN) {
        playerRef.sendMessage(Message.raw("Unknown item: " + itemId));
        return;
    }

    // Try to add to combined hotbar + storage
    CombinedItemContainer combined = player.getInventory().getCombinedHotbarFirst();
    ItemStackTransaction result = combined.addItemStack(itemStack);
    ItemStack remainder = result.getRemainder();

    int added = quantity - (remainder != null ? remainder.getQuantity() : 0);

    if (added == quantity) {
        playerRef.sendMessage(Message.raw("Received " + quantity + "x " + itemId));
    } else if (added > 0) {
        playerRef.sendMessage(Message.raw(
            "Received " + added + "x " + itemId + " (inventory full, " +
            (quantity - added) + " dropped)"
        ));
        // Optionally drop remainder on ground
    } else {
        playerRef.sendMessage(Message.raw("Inventory full!"));
    }
}
```

### ListTransaction<T extends Transaction>
```java
boolean succeeded()
List<T> getList()
int size()
static <T> ListTransaction<T> getEmptyTransaction(boolean success)
```

### MoveTransaction<T extends Transaction>
Wraps source and destination transactions for move operations.

---

## Container Iteration

### forEach Pattern

Use `forEach` to iterate over all slots in a container:

```java
ItemContainer container = inventory.getHotbar();

container.forEach((slot, itemStack) -> {
    if (!itemStack.isEmpty()) {
        String itemId = itemStack.getItemId();
        int quantity = itemStack.getQuantity();
        System.out.println("Slot " + slot + ": " + itemId + " x" + quantity);
    }
});
```

**Count items matching a condition:**
```java
int weaponCount = 0;
container.forEach((slot, itemStack) -> {
    if (!itemStack.isEmpty() && itemStack.getItem().getWeapon() != null) {
        weaponCount++;
    }
});
```

**Find first matching item:**
```java
short foundSlot = -1;
container.forEach((slot, itemStack) -> {
    if (foundSlot == -1 && itemStack.getItemId().equals("Tool_Pickaxe_Iron")) {
        foundSlot = slot;
    }
});
```

**Note:** The `forEach` consumer receives `(short slotIndex, ItemStack itemStack)` via `ShortObjectConsumer`.

---

## Usage Examples

### Get Player Inventory
```java
Player player = store.getComponent(ref, Player.getComponentType());
Inventory inventory = player.getInventory();
```

### Check Held Item
```java
ItemStack heldItem = inventory.getItemInHand();
if (!heldItem.isEmpty()) {
    String itemId = heldItem.getItemId();
    int count = heldItem.getQuantity();
    playerRef.sendMessage(Message.raw("Holding: " + itemId + " x" + count));
}
```

### Add Item to Inventory
```java
ItemStack newItem = new ItemStack("my_item", 10);
ItemContainer hotbar = inventory.getHotbar();
ItemStackTransaction result = hotbar.addItemStack(newItem);
if (result.succeeded()) {
    playerRef.sendMessage(Message.raw("Item added!"));
} else {
    ItemStack remainder = result.getRemainder();
    // Handle overflow
}
```

### Move Items Between Containers
```java
ItemContainer hotbar = inventory.getHotbar();
ItemContainer storage = inventory.getStorage();

// Move all from hotbar to storage
ListTransaction<MoveTransaction<ItemStackTransaction>> result =
    hotbar.moveAllItemStacksTo(storage);

if (result.succeeded()) {
    playerRef.sendMessage(Message.raw("Items moved to storage"));
}
```

### Listen for Inventory Changes
```java
ItemContainer hotbar = inventory.getHotbar();
hotbar.registerChangeEvent(event -> {
    playerRef.sendMessage(Message.raw("Hotbar changed!"));
});
```

### Sort Storage
```java
inventory.sortStorage();
```

### Create ItemStack with Metadata
```java
ItemStack item = new ItemStack("magic_sword", 1)
    .withDurability(100.0)
    .withMaxDurability(100.0)
    .withMetadata("enchantment", someCodec, enchantmentData);
```

### Access via LivingEntity
```java
LivingEntity entity = ...;
Inventory inv = entity.getInventory();
entity.setInventory(newInventory);
entity.setInventory(newInventory, true);  // with notification
```

---

## Crafting System

Types related to crafting recipes and requirements.

> **See also:** [Interactions System](interactions.md)

---

## CraftingRecipe
**Package:** `com.hypixel.hytale.server.core.asset.type.item.config`

Asset type for crafting recipes. Returned by `CraftRecipeEvent.getCraftedRecipe()`.

### Constants
```java
static final String FIELDCRAFT_REQUIREMENT  // Fieldcraft bench requirement ID
```

### Static Methods
```java
static AssetStore<String, CraftingRecipe, ...> getAssetStore()
static AssetMap<String, CraftingRecipe> getAssetMap()
static String generateIdFromItemRecipe(Item item, int index)  // Generate recipe ID from item
```

### Identity
```java
String getId()  // Unique recipe identifier
```

### Inputs & Outputs
```java
MaterialQuantity[] getInput()         // Required materials
MaterialQuantity[] getOutputs()       // All output items
MaterialQuantity getPrimaryOutput()   // Main crafted item
```

### Requirements
```java
BenchRequirement[] getBenchRequirement()           // Required crafting benches
boolean isRestrictedByBenchTierLevel(String benchId, int tierLevel)  // Check tier restriction
float getTimeSeconds()                             // Crafting time
boolean isKnowledgeRequired()                      // Whether recipe must be learned
int getRequiredMemoriesLevel()                     // Required memories level
```

### Network
```java
CraftingRecipe toPacket(String id)  // Convert to network packet format
```

### Usage Example
```java
// In a CraftRecipeEvent handler
public void handle(..., CraftRecipeEvent.Pre event) {
    CraftingRecipe recipe = event.getCraftedRecipe();

    // Get what's being crafted
    MaterialQuantity output = recipe.getPrimaryOutput();
    int quantity = event.getQuantity();

    // Check crafting time
    float seconds = recipe.getTimeSeconds();

    // Check required materials
    MaterialQuantity[] inputs = recipe.getInput();
    for (MaterialQuantity input : inputs) {
        String itemId = input.getItemId();
        int needed = input.getQuantity();
    }

    // Check bench requirements
    BenchRequirement[] benches = recipe.getBenchRequirement();
    for (BenchRequirement bench : benches) {
        if (bench.type == BenchType.Crafting) {
            // Standard crafting bench required
        }
    }
}
```

> **See also:** [Asset Registry](assets.md#asset-types)

---

## BenchRequirement
**Package:** `com.hypixel.hytale.protocol`

Specifies crafting bench requirements for a recipe.

### Fields
```java
BenchType type           // Type of bench required
String id                // Specific bench ID (optional)
String[] categories      // Bench categories (optional)
int requiredTierLevel    // Minimum bench tier level
```

### Usage
```java
BenchRequirement[] benches = recipe.getBenchRequirement();
for (BenchRequirement bench : benches) {
    BenchType type = bench.type;
    int tierLevel = bench.requiredTierLevel;

    if (type == BenchType.Processing) {
        // Requires a processing station
    }
}
```

---

## BenchType
**Package:** `com.hypixel.hytale.protocol`

Enum for types of crafting benches.

```java
public enum BenchType {
    Crafting,           // Standard crafting table
    Processing,         // Processing station (smelting, etc.)
    DiagramCrafting,    // Blueprint-based crafting
    StructuralCrafting  // Building/structural crafting

    int getValue()                        // Get numeric value
    static BenchType fromValue(int value) // Get from numeric value
}
```

---

## Crafting Events

Events related to crafting and recipes.

### CraftRecipeEvent

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

Abstract base ECS event for crafting. Extends `CancellableEcsEvent`. Has two concrete variants for pre/post crafting.

#### Base Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getCraftedRecipe()` | `CraftingRecipe` | The recipe being crafted |
| `getQuantity()` | `int` | Number of items being crafted |

### CraftRecipeEvent.Pre

Fired before crafting completes. Cancellable.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getCraftedRecipe()` | `CraftingRecipe` | The recipe being crafted |
| `getQuantity()` | `int` | Number of items being crafted |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel the crafting |

### CraftRecipeEvent.Post

Fired after crafting completes.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getCraftedRecipe()` | `CraftingRecipe` | The recipe that was crafted |
| `getQuantity()` | `int` | Number of items crafted |

### Crafting Event Example

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.CraftRecipeEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class CraftingSystem extends EntityEventSystem<EntityStore, CraftRecipeEvent.Pre> {

    public CraftingSystem() {
        super(CraftRecipeEvent.Pre.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       CraftRecipeEvent.Pre event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            var recipe = event.getCraftedRecipe();
            int quantity = event.getQuantity();
            player.sendMessage(Message.raw("Crafting " + quantity + " items..."));

            // Optionally cancel the craft
            // event.setCancelled(true);
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

### Crafting Event Registration

```java
@Override
protected void setup() {
    // Listen for pre-craft (can cancel)
    getEntityStoreRegistry().registerSystem(new CraftingSystem());

    // Or listen for post-craft (after completion)
    getEntityStoreRegistry().registerSystem(
        new EntityEventSystem<EntityStore, CraftRecipeEvent.Post>(CraftRecipeEvent.Post.class) {
            @Override
            public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                               Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                               CraftRecipeEvent.Post event) {
                // Handle post-craft
            }

            @Override
            public Query<EntityStore> getQuery() {
                return Player.getComponentType();
            }
        }
    );
}
```

---

## Inventory Events

Events related to inventory operations (dropping items, switching slots, picking up items, inventory changes).

### Event Summary

**Package:** `com.hypixel.hytale.server.core.inventory`

| Class | Description |
|-------|-------------|
| `InventoryChangeEvent` | Inventory contents change (ECS event) |

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

| Class | Description |
|-------|-------------|
| `DropItemEvent` | Item is dropped (has `Drop` and `PlayerRequest` variants) |
| `InteractivelyPickupItemEvent` | Item is picked up interactively |
| `SwitchActiveSlotEvent` | Active inventory slot changes |

---

### InventoryChangeEvent

**Package:** `com.hypixel.hytale.server.core.inventory`

ECS event (extends `EcsEvent`) fired when an inventory's contents change. Handle it with an `EntityEventSystem`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getComponentType()` | `ComponentType<EntityStore, ? extends InventoryComponent>` | The inventory component type |
| `getInventory()` | `InventoryComponent` | The inventory component that changed |
| `getItemContainer()` | `ItemContainer` | The container that changed |
| `getTransaction()` | `Transaction` | The transaction details |

### Usage Example

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryChangeEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class InventoryChangeSystem extends EntityEventSystem<EntityStore, InventoryChangeEvent> {

    public InventoryChangeSystem() {
        super(InventoryChangeEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       InventoryChangeEvent event) {
        var container = event.getItemContainer();
        var transaction = event.getTransaction();
        System.out.println("Inventory changed: " + transaction);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

### DropItemEvent

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

ECS event fired when an item is dropped. Extends `CancellableEcsEvent`. The base class has no item/position accessors; use the variant subclasses:
- `DropItemEvent.Drop` - General item drop. Provides `getItemStack()` / `setItemStack(ItemStack)` and `getThrowSpeed()` / `setThrowSpeed(float)`.
- `DropItemEvent.PlayerRequest` - Player-initiated drop. Provides `getInventorySectionId()` (`int`) and `getSlotId()` (`short`).

**`DropItemEvent.Drop`**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getItemStack()` | `ItemStack` | The item being dropped |
| `getThrowSpeed()` | `float` | Throw speed of the drop |

**`DropItemEvent.PlayerRequest`**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getInventorySectionId()` | `int` | Section the drop originates from |
| `getSlotId()` | `short` | Slot the drop originates from |

---

### InteractivelyPickupItemEvent

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

ECS event fired when an item is picked up interactively (e.g., player collecting items).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getItemStack()` | `ItemStack` | The item being picked up |

---

### SwitchActiveSlotEvent

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

ECS event fired when the active inventory slot changes (e.g., player switching hotbar slot).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPreviousSlot()` | `int` | The previous active slot |
| `getNewSlot()` | `byte` | The new active slot |

### ECS Inventory Event Example

For ECS events, use an `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.SwitchActiveSlotEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class SlotSwitchSystem extends EntityEventSystem<EntityStore, SwitchActiveSlotEvent> {

    public SlotSwitchSystem() {
        super(SwitchActiveSlotEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       SwitchActiveSlotEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            player.sendMessage(Message.raw(
                "Switched from slot " + event.getPreviousSlot() + " to " + event.getNewSlot()
            ));
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

### Registration

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new SlotSwitchSystem());
}
```

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 inventory system (verified against `HytaleServer.jar`).

- **Symptom:** an item given with the wrong case (e.g. `plant_fruit_apple`) is accepted but renders as a `?` placeholder on the client → item ids are **case-sensitive on the client**, while `getItem()` resolves loosely server-side (so a mis-cased id is not `Item.UNKNOWN`). Fix: use the exact asset-file casing, e.g. `Plant_Fruit_Apple`.
- **Symptom:** `ItemStack.isValid()` rejects an item you know exists → `isValid()` can reject valid items in some cases. Fix: test `stack.getItem() == Item.UNKNOWN` instead (see [Validating Item IDs](#validating-item-ids)).
- **Symptom:** items appear not to be added even though there is space → you discarded the transaction result. Fix: check `result.succeeded()` and inspect `result.getRemainder()` rather than assuming success.
- **`Container must have something to drop!`** → a drop operation was called on an empty container. Fix: guard with `!container.isEmpty()` first.
- **`setSlot(int, ItemStack) is not supported in EmptyItemContainer`** → you mutated the shared empty-container singleton (e.g. a section the entity doesn't have). Fix: operate on a real section/container obtained from the live `Inventory`.
- **`cannot select an active slot`** → an active-slot setter received a slot that the target section can't make active. Fix: pass a valid in-range slot for that section.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
