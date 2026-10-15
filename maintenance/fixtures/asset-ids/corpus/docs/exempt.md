# Exemptions that apply

Every id that starts with `MyMod_` is a placeholder for an id of your own, and so is `"Chain_Named"`.
This page also builds on the custom-food pack.

`Server/Item/Items/Weapon/Sword_Page.json`

```json
{ "Name": "defines Sword_Page" }
```

```json
{ "ItemId": "Sword_Page", "Next": "Sword_Page" }
```

```json
// Server/Item/Interactions/Int_Page.json
{ "Type": "Simple" }
```

```json
{ "Next": "Int_Page" }
```

```json
[ { "Next": "MyMod_Step" }, { "Next": "Chain_Named" }, { "Next": "MyMod" }, { "Next": "Other_Step" }, { "ItemId": "MyMod_Item" } ]
```

```json
[ { "ItemId": "Food_Snack" }, { "ItemId": "Drop_Chick" } ]
```
