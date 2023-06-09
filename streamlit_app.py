import subprocess
import plotly
import numpy as np
from stl import mesh  # pip install numpy-stl
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
import os
import time
import math
import base64 # to download from html link

def create_download_link(val, filename):
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.stl">Download mesh</a>'

def stl2mesh3d(stl_mesh):
    # stl_mesh is read by nympy-stl from an stl file; it is  an array of faces/triangles (i.e. three 3d points)
    # This function extracts the unique vertices and the lists I, J, K to define a Plotly mesh3d
    p, q, r = stl_mesh.vectors.shape #(p, 3, 3)
    # the array stl_mesh.vectors.reshape(p*q, r) can contain multiple copies of the same vertex;
    # extract unique vertices from all mesh triangles
    vertices, ixr = np.unique(stl_mesh.vectors.reshape(p*q, r), return_inverse=True, axis=0)
    I = np.take(ixr, [3*k for k in range(p)])
    J = np.take(ixr, [3*k+1 for k in range(p)])
    K = np.take(ixr, [3*k+2 for k in range(p)])
    return vertices, I, J, K

def figure_mesh(filename):
  my_mesh = mesh.Mesh.from_file(filename)
  vertices, I, J, K = stl2mesh3d(my_mesh)
  x, y, z = vertices.T
  colorscale= [[0, '#e5dee5'], [1, '#e5dee5']]
  mesh3D = go.Mesh3d(
              x=x,
              y=y,
              z=z,
              i=I,
              j=J,
              k=K,
              name='mesh',
              showscale=False,
              colorscale=colorscale, 
              intensity=z,
              flatshading=True,)
  title = "Mesh"
  layout = go.Layout(
              paper_bgcolor='rgb(1,1,1)',
              title_text=None,# title_x=0.5, font_color='white',
              width=800,
              height=800,
              scene_camera=dict(eye=dict(x=1.25, y=-1.25, z=1)),
              scene_xaxis_visible=True,
              scene_yaxis_visible=True,
              scene_zaxis_visible=False)
  fig = go.Figure(data=[mesh3D], layout=layout)

  fig.data[0].update(lighting=dict(ambient= 0.18,
                                   diffuse= 1,
                                   fresnel=  .1,
                                   specular= 1,
                                   roughness= .1,
                                   facenormalsepsilon=0))
  fig.data[0].update(lightposition=dict(x=3000,
                                        y=3000,
                                        z=10000));
  fig.update_scenes(aspectmode='data')
  fig.write_html("file_stl.html")
  return fig

def find_center(ind, ref, pos, ali):
    conv = 2*math.cos(30*math.pi/180)
    cos = math.cos(30*math.pi/180)
    prev_center = blocks[ref]['center']
    center = [prev_center[0], prev_center[1]]
    ref_y = blocks[ref]['ext'][1]/2
    ref_x = blocks[ref]['ext'][0]/2
    bl_y = blocks[ind]['ext'][1]/2
    bl_x = blocks[ind]['ext'][0]/2
    ref_wx = blocks[ref]['wal'][0]
    ref_wy = blocks[ref]['wal'][1]
    bl_wx = blocks[ind]['wal'][0]
    bl_wy = blocks[ind]['wal'][0]
    honey = (blocks[ref]['shape'] == 'Honeycomb' and blocks[ind]['shape'] == 'Honeycomb')
    if blocks[ref]['shape'] == 'Honeycomb':
        ref_x *= 2/conv
        ref_y = blocks[ref]['ext'][0]/2
    if blocks[ind]['shape'] == 'Honeycomb':
        bl_x *= 2/conv
        bl_y = blocks[ind]['ext'][0]/2
    w_overlap_y = min([ref_wy, bl_wy])
    w_overlap_x = min([ref_wx, bl_wx])
    move_x = ref_x + bl_x - w_overlap_x
    move_y = ref_y + bl_y - w_overlap_y
    if pos == 'back':
        center[1] += move_y
    elif pos == 'front':
        center[1] -= move_y
    elif pos == 'right':
        center[0] += move_x
    elif pos == 'left':
        center[0] -= move_x
    if ali == 'top' and not honey:
        center[1] += ref_y - bl_y
    elif ali == 'bottom' and not honey:
        center[1] -= ref_y - bl_y
    elif ali == 'right':
        center[0] += ref_x - bl_x
    elif ali == 'left':
        center[0] -= ref_x - bl_x
    if honey and ali in ('top', 'bottom'):
        center[0] = prev_center[0]
        # don't use normal wall, but wall that take into account the slope
        x_offset = blocks[ref]['ext'][0]*cos - w_overlap_x * cos - blocks[ref]['ext'][0]*math.sqrt(3)/3 + blocks[ind]['ext'][0]*math.sqrt(3)/3
        y_offset = blocks[ref]['ext'][0]/2  - w_overlap_x/2
        if pos == 'left':
            center[0] -= x_offset
        elif pos == 'right':
            center[0] += x_offset
        if ali == 'top':
            center[1] += y_offset
        elif ali == 'bottom':
            center[1] -= y_offset
    return center


def add_block(ind, shape, size_int, size_ext, height, pat, h_dia, h_thick):
    if shape == 'Square':
        if pat == 'Honeycomb':
            return str(f"""
    color("{color[ind-1]}")
    translate([{blocks[index]['center'][0]},{blocks[index]['center'][1]},0])
    rhbox([{size_int[0]},{size_int[1]}], [{size_ext[0]},{size_ext[1]}], {height}, h_dia={h_dia}, h_thick={h_thick});
    """)
        else:
            return str(f"""
    color("{color[ind-1]}")
    translate([{blocks[index]['center'][0]},{blocks[index]['center'][1]},0])
    rbox([{size_int[0]},{size_int[1]}], [{size_ext[0]},{size_ext[1]}], {height}) ;
    """)
    else:
        if pat == 'Honeycomb':
            return str(f"""
    color("{color[ind-1]}")
    translate([{blocks[index]['center'][0]},{blocks[index]['center'][1]},0])
    hhbox({size_int[0]}, {size_ext[0]}, {height}, h_dia={h_dia}, h_thick={h_thick});
    """)
        else:
            return str(f"""
    color("{color[ind-1]}")
    translate([{blocks[index]['center'][0]},{blocks[index]['center'][1]},0])
    hbox({size_int[0]}, {size_ext[0]}, {height}) ;
    """)


if __name__ == "__main__":
    color = ['yellow', 'red', 'navy', 'green', 'purple', 'silver', 'orange', 'indigo', 'teal', 'darkslategray',
    'yellowgreen', 'cyan', 'cornflowerblue', 'magenta', 'tan', 'darkred', 'deeppink', 'olive', 'lightsalmon', 'mocassin', 'rosybrown']

    if 'blocks' not in st.session_state:
        st.session_state['blocks'] = dict()
    blocks = st.session_state['blocks']
    if 'blocks_text' not in st.session_state:
        st.session_state['blocks_text'] = dict()
    if len(blocks) > len(color)-2:
        n_colors = len(blocks)//len(color)
        color = color * (n_colors+2)

    start_text = """
include <honeycomb.scad>
include <desk_organizer.scad>
$fn = 40;
r_perc = 7;
base = 2;
"""

    st.title('Desk Organizer Generator!')
    st.write('Generate a 3D model for a custom Desk Organizer from simple building blocks.')
    st.write('Visit the instructions on the [Printables page](https://www.printables.com/it/model/498850-desk-organizer-generator)!')
    st.write('Note: the Honeycomb pattern increases the rendering time.')

    blocks_text = st.session_state['blocks_text']
    # Add blocks 
    with st.form('Add '):
        st.markdown('**Add a block to the organizer**')
        if blocks:
            col1, col2, col3 = st.columns(3)
            with col1:
                ref = st.selectbox('Select the reference block', sorted(list(blocks), reverse=True))
            with col2:
                pos = st.selectbox('Where to add the block', [ 'right', 'left', 'back', 'front'])
            with col3:
                ali = st.selectbox('Alignment', ['center', 'right', 'left', 'top', 'bottom'])
            index = len(blocks) + 1
            center = False
        else:
            center = True
            index = 1
            ref = 0
            pos = None
            ali = None
        col1, col2, col3 = st.columns(3)
        st.write('The Honeycomb shape only considers the X values')
        with col1:
            shape = st.selectbox('Block Shape', ['Square', 'Honeycomb'])
        with col2:
            x_size = st.number_input('X size', value=40.0)
        with col3:
            y_size = st.number_input('Y size', value=40.0)
        col1, col2, col3 = st.columns(3)
        with col1:
            height = st.number_input('Height', value=70.0)
        with col2:
            x_wall = st.number_input('Wall X thickness', value=2.0)
        with col3:
            y_wall = st.number_input('Wall Y thickness', value=2.0)
        col1, col2, col3 = st.columns(3)
        with col1:
            pat = st.selectbox('Wall pattern', ['Solid', 'Honeycomb',])
        h_dia = None
        h_thick = None
        with col2:
            h_dia = st.number_input('Honeycomb hexagon height', value=4.0)
        with col3:
            h_thick = st.number_input('Honeycomb line size', value=1.0)
        
        col1, col2 = st.columns(2)
        with col1:
            add = st.form_submit_button("Add block")
            if add:
                blocks[index] = dict()
                if shape == 'Honeycomb':
                    y_size = x_size
                    y_wall = x_wall
                blocks[index]['shape'] = shape
                blocks[index]['int'] = [x_size, y_size]
                blocks[index]['ext'] = [x_size + x_wall*2, y_size + y_wall*2]
                blocks[index]['wal'] = [x_wall, y_wall]
                if center:
                    blocks[index]['center'] = [0,0]
                else:
                    blocks[index]['center'] = find_center(index, ref, pos, ali)
                blocks_text[index] = add_block(index, shape, blocks[index]['int'], blocks[index]['ext'], height, pat, h_dia, h_thick)
                st.session_state['blocks'].update(blocks)
                st.session_state['blocks_text'].update(blocks_text)
                st.experimental_rerun()
        with col2:
            if blocks:
                remove = st.form_submit_button("Remove block")
                if remove:
                    if ref not in blocks:
                        st.warning(f'Block {ref} not found. No block removed.', icon="⚠️")
                    else:
                        st.session_state['blocks'].pop(ref)
                        st.session_state['blocks_text'].pop(ref)
                        st.experimental_rerun()


    if not blocks:
             st.stop()

    run_text = str()
    for index in st.session_state['blocks_text']:
        run_text = run_text + st.session_state['blocks_text'][index]

    run_text = start_text + run_text
    #PREPARE FILES
    with open('run.scad', 'w') as f:
        f.write(run_text)
    st.write('The program renders with OpenScad, full rendering of a mesh takes a while. If you want to run it faster on your pc, check out the [Github page](https://github.com/lmonari5/desk_organizer_generator.git).')

    preview = False
    if not st.button('Render'):
        preview = True
    if preview:
        subprocess.run('xvfb-run -a openscad -o preview.png --camera 0,0,0,30,0,0,0 --autocenter --viewall  --projection=ortho run.scad', shell = True)
    else:
        start = time.time()
        # run openscad
        with st.spinner('Rendering in progress...'):    
            subprocess.run(f'openscad run.scad -o file.stl', shell = True)
        end = time.time()
        st.success(f'Rendered in {int(end-start)} seconds', icon="✅")

    if preview:
        if 'preview.png' not in os.listdir():
            st.error('OpenScad was not able to generate the preview', icon="🚨")
            st.stop()
        st.write('Preview image:')
        colors_text = 'Blocks colors:'
        for index in st.session_state['blocks']:
            colors_text += f' <span style="color:{color[index-1]}">block {index},</span>'
        st.markdown(colors_text, unsafe_allow_html=True)
        image = Image.open('preview.png')
        st.image(image, caption='Openscad preview')
        image.close()
    else:
        if 'file.stl' not in os.listdir():
            st.error('OpenScad was not able to generate the mesh', icon="🚨")
            st.stop()
        with open(f"file.stl", "rb") as file:
            html = create_download_link(file.read(), "model")
            st.markdown("Please, put a like [on Printables](https://www.printables.com/it/model/498850-desk-organizer-generator) to support the project!", unsafe_allow_html=True)
            st.markdown("I am a student who enjoys 3D printing and programming. If you want to support me with a coffee, just [click here!](https://www.paypal.com/donate/?hosted_button_id=V4LJ3Z3B3KXRY)", unsafe_allow_html=True)
            st.markdown(html, unsafe_allow_html=True)
        st.write('Interactive mesh preview:')
        st.plotly_chart(figure_mesh(f'file.stl'), use_container_width=True)
