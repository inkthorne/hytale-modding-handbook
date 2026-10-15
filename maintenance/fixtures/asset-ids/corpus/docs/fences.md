# Fences

Comments and an ellipsis make a fence unparseable; the pairs are still read.

```json
{
  // a comment
  "Next": "Int_Bad1",
  "Extra": ...,
  "Interactions": ["Int_Bad1b", ...]
}
```

A fragment without braces:

```json
"Next": "Int_Bad2"
```

An untagged fence that is JSON:

```
{ "Next": "Int_Bad3" }
```

An untagged fence that only has a quoted fragment in a tree, and a java fence:

```
Tree
└── "Next": "Int_Bad4"
```

```java
String s = "{ \"Next\": \"Int_Bad5\" }";
Map.of("Next", "Int_Bad5");
```

1. A fence nested in a list item:

   ```json
   { "Next": "Int_Bad6" }
   ```

> A blockquoted fence is a fence:
>
> ```json
> { "Next": "Int_Bad7" }
> ```

> And so is a quoted java one, which is counted and not read:
>
> ```java
> Map.of("Next", "Int_Bad8");
> ```
