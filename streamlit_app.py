ValueError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/realproject/streamlit_app.py", line 206, in <module>
    fig_map.update_traces(marker=dict(size_max=50))
File "/home/adminuser/venv/lib/python3.11/site-packages/plotly/graph_objs/_figure.py", line 188, in update_traces
    return super().update_traces(
           ^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.11/site-packages/plotly/basedatatypes.py", line 1388, in update_traces
    trace.update(patch, overwrite=overwrite, **kwargs)
File "/home/adminuser/venv/lib/python3.11/site-packages/plotly/basedatatypes.py", line 5195, in update
    BaseFigure._perform_update(self, kwargs, overwrite=overwrite)
File "/home/adminuser/venv/lib/python3.11/site-packages/plotly/basedatatypes.py", line 3971, in _perform_update
    BaseFigure._perform_update(plotly_obj[key], val)
File "/home/adminuser/venv/lib/python3.11/site-packages/plotly/basedatatypes.py", line 3949, in _perform_update
    raise err
