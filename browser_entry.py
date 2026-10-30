"""Browser-only export adapter; the original app and model remain unchanged."""
import base64
import html
import runpy
import streamlit as st


def browser_download(label, data, file_name='download.csv', mime='text/csv', **kwargs):
    # A browser has no persistent Streamlit /media server. Keep the exact CSV
    # bytes supplied by the original app and download them directly as a data URI.
    payload = data.encode('utf-8') if isinstance(data, str) else bytes(data)
    uri = 'data:' + html.escape(mime or 'text/csv', quote=True) + ';base64,'
    uri += base64.b64encode(payload).decode('ascii')
    st.markdown(
        '<a href="' + uri + '" download="' + html.escape(file_name, quote=True)
        + '" style="display:inline-block;padding:0.5rem 0.8rem;border:1px solid '
        '#b5c9c5;border-radius:0.5rem;color:#126e63;text-decoration:none">'
        + html.escape(label) + '</a>',
        unsafe_allow_html=True,
    )
    return False


st.download_button = browser_download
runpy.run_path('app.py', run_name='__main__')
