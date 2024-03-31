# 📚 Internals

## Design

Add here some documentation for your design.

```{mermaid} figures/design.mmd
```


## MyApp

### Requirements

```{item} REQ-MY_APP_PROJECT_DIR-0.0.1 External project path
   :status: Approved

   It **shall** support projects directories which are not the current directory.
   The application shall not expect that the project directory is the current directory.
```

```{item} REQ-MY_APP_LOGGING-0.0.1 Create log file
   :status: Not implemented

   It **shall** generate a log file and overwrite it for every run.
   This will ease debugging the application in production.
   The user can attach the log file to the bug report.
```

### Reports



```{item-matrix} Trace requirements to implementation
    :source: REQ-MY_APP
    :target: IMPL
    :sourcetitle: Requirement
    :targettitle: Implementation
    :stats:
```

```{item-piechart} Implementation coverage chart
    :id_set: REQ-MY_APP IMPL
    :label_set: Not implemented, Implemented
    :sourcetype: fulfilled_by
```

```{item-matrix} Requirements to test case description traceability
    :source: REQ-MY_APP
    :target: "[IU]TEST"
    :sourcetitle: Requirements
    :targettitle: Test cases
    :sourcecolumns: status
    :group: bottom
    :stats:
```

### API

Add here some documentation for your class.

```{eval-rst}
.. autoclass:: clanguru.my_app::MyApp
   :members:
   :undoc-members:
```

## Testing

```{eval-rst}
.. automodule:: test_my_app
   :members:
   :show-inheritance:
```
