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
