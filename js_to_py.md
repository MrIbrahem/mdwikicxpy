replace in VsCode with match case:

```
([a-z]+)([A-Z])([a-z]+)
```

replace with:

```
$1_\L$2$3
```
