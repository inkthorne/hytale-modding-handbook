# Excerpts

An excerpt of `Server/Item/Interactions/Int_J.json`, which ships this wrong-kind value:

```json
{ "Next": "Fx_A" }
```

The same id, said to come from a file that does not contain it, `Server/Item/Interactions/Int_B.json`:

```json
{ "Next": "Fx_A" }
```

And from a file that does not exist, `Server/Item/Interactions/Int_Nope.json`:

```json
{ "Next": "Fx_A" }
```

The same id, in a file that ships it under a different key, `Server/Item/Interactions/Int_J.json` (EffectId):

```json
{ "Next": "Fx_D" }
```

A string the file holds only as a map key, from `Server/Item/Items/Item_H.json`:

```json
{ "Next": "B0" }
```

Unlike `Server/Item/Interactions/Int_J.json`, which ships Fx_A as its Next,
this is an interaction I invented for the page, with the id under another key:

```json
{ "Next": "Fx_D" }
```
