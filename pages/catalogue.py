Pasted text(20260926-091028).txt
Document
import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
import base64
import html

from PIL import Image, ImageOps


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="🧥",
    layout="wide",
)


# =========================================================
# SUPABASE CONNECTION
# =========================================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


supabase = get_supabase()


# =========================================================
# STORAGE
# =========================================================

BUCKET_NAME = "leather-images"


def get_image_url(filename):

    if not filename:
        return None

    filename = str(filename).strip()

    if not filename:
        return None

    return (
        f"{st.secrets['SUPABASE_URL']}"
        f"/storage/v1/object/public/"
        f"{BUCKET_NAME}/"
        f"{quote(filename)}"
    )


# =========================================================
# LOAD PRODUCTS
# =========================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def load_products():

    response = (
        supabase
        .table("leather_products")
        .select(
            """
            leather_id,
            article_name,
            color,
            thickness,
            tannage,
            animal,
            origin,
            main_photo,
            closeup_photo,
            is_active
            """
        )
        .eq("is_active", True)
        .order("leather_id")
        .execute()
    )

    return response.data or []


try:

    products = load_products()

except Exception as e:

    st.error(
        "Unable to load the leather catalogue."
    )

    st.exception(e)

    st.stop()


# =========================================================
# IMAGE SETTINGS
# =========================================================

# Catalogue cards
CARD_SIZE = (1200, 675)


# Detail viewer.
#
# This is intentionally lower than before so that
# the photo + complete information fit inside the
# dialog without unnecessary vertical scrolling.
DETAIL_VIEWER_HEIGHT = 500


# =========================================================
# DOWNLOAD IMAGE
# =========================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def load_image(image_url):

    if not image_url:
        return None

    try:

        with urlopen(
            image_url,
            timeout=20,
        ) as response:

            image_bytes = response.read()

        image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

        return image

    except Exception:

        return None


# =========================================================
# IMAGE -> BASE64
# =========================================================

def image_to_base64(image):

    if image is None:
        return None

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=92,
        optimize=True,
    )

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


# =========================================================
# CREATE UNIFORM CARD IMAGE
# =========================================================

def make_card_image(image):

    if image is None:
        return None

    fitted = ImageOps.contain(
        image,
        CARD_SIZE,
    )

    canvas = Image.new(
        "RGB",
        CARD_SIZE,
        "white",
    )

    x = (
        CARD_SIZE[0]
        - fitted.width
    ) // 2

    y = (
        CARD_SIZE[1]
        - fitted.height
    ) // 2

    canvas.paste(
        fitted,
        (x, y),
    )

    return canvas


# =========================================================
# AUTO SLIDING CATALOGUE PHOTO
#
# Main photo
#     ↓
# 5 seconds
#     ↓
# Close-up
#     ↓
# 5 seconds
#     ↓
# Main photo
#
# No Streamlit rerun is required.
# =========================================================

def auto_slide_image(
    main_url,
    closeup_url,
    height=220,
    key="",
):

    if not main_url and not closeup_url:

        st.info(
            "Image unavailable"
        )

        return


    # -----------------------------------------------------
    # ONLY MAIN PHOTO
    # -----------------------------------------------------

    if main_url and not closeup_url:

        safe_main_url = html.escape(
            main_url,
            quote=True,
        )

        iframe_html = f"""
        <!DOCTYPE html>

        <html>

        <head>

        <style>

        html,
        body {{
            margin: 0;
            padding: 0;

            width: 100%;
            height: 100%;

            overflow: hidden;

            background: white;
        }}

        .photo {{
            width: 100%;
            height: 100%;

            display: flex;

            align-items: center;
            justify-content: center;

            overflow: hidden;

            background: white;
        }}

        img {{
            width: 100%;
            height: 100%;

            object-fit: contain;

            display: block;
        }}

        </style>

        </head>

        <body>

        <div class="photo">

            <img
                src="{safe_main_url}"
                alt="Leather photo"
            >

        </div>

        </body>

        </html>
        """

        st.iframe(
            iframe_html,
            height=height,
        )

        return


    # -----------------------------------------------------
    # MAIN + CLOSE-UP
    # -----------------------------------------------------

    safe_main_url = html.escape(
        main_url,
        quote=True,
    )

    safe_closeup_url = html.escape(
        closeup_url,
        quote=True,
    )


    iframe_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width,
                 initial-scale=1.0"
    >

    <style>

    * {{
        box-sizing: border-box;
    }}


    html,
    body {{

        margin: 0;
        padding: 0;

        width: 100%;
        height: 100%;

        overflow: hidden;

        background: white;
    }}


    .slider {{

        position: relative;

        width: 100%;
        height: 100%;

        overflow: hidden;

        background: white;
    }}


    .slide {{

        position: absolute;

        inset: 0;

        width: 100%;
        height: 100%;

        display: flex;

        align-items: center;
        justify-content: center;

        opacity: 0;

        transition:
            opacity 0.8s ease-in-out;
    }}


    .slide.active {{

        opacity: 1;
    }}


    .slide img {{

        width: 100%;
        height: 100%;

        object-fit: contain;

        display: block;
    }}


    .photo-label {{

        position: absolute;

        right: 10px;
        bottom: 10px;

        padding:
            4px 8px;

        border-radius: 5px;

        background:
            rgba(
                0,
                0,
                0,
                0.60
            );

        color: white;

        font-size: 10px;

        z-index: 5;

        opacity: 0;

        transition:
            opacity 0.4s ease;
    }}


    .slider:hover .photo-label {{

        opacity: 1;
    }}


    </style>

    </head>


    <body>


    <div
        class="slider"
        id="slider"
    >


        <div
            class="slide active"
            id="mainSlide"
        >

            <img
                src="{safe_main_url}"
                alt="Main leather photo"
            >

        </div>


        <div
            class="slide"
            id="closeupSlide"
        >

            <img
                src="{safe_closeup_url}"
                alt="Leather close-up photo"
            >

        </div>


        <div
            class="photo-label"
            id="photoLabel"
        >
            Main
        </div>


    </div>


    <script>

    let showingMain = true;


    const mainSlide =
        document.getElementById(
            "mainSlide"
        );


    const closeupSlide =
        document.getElementById(
            "closeupSlide"
        );


    const photoLabel =
        document.getElementById(
            "photoLabel"
        );


    function switchPhoto() {{

        showingMain =
            !showingMain;


        if (showingMain) {{

            mainSlide.classList.add(
                "active"
            );

            closeupSlide.classList.remove(
                "active"
            );

            photoLabel.textContent =
                "Main";

        }} else {{

            mainSlide.classList.remove(
                "active"
            );

            closeupSlide.classList.add(
                "active"
            );

            photoLabel.textContent =
                "Close-up";
        }}
    }}


    // ---------------------------------------------------
    // CHANGE EVERY 5 SECONDS
    // ---------------------------------------------------

    setInterval(
        switchPhoto,
        5000
    );


    </script>


    </body>

    </html>
    """


    st.iframe(
        iframe_html,
        height=height,
    )


# =========================================================
# PROFESSIONAL INTERACTIVE DETAIL VIEWER
#
# IMPORTANT:
#
# Initial state = COMPLETE PHOTO FITTED.
#
# It is NOT zoomed initially.
#
# Mouse wheel:
#     Zoom in / out
#
# Mouse drag:
#     Move in every direction
#
# Double click:
#     Reset
#
# + / -:
#     Zoom
#
# Reset:
#     Fit photo back to screen
# =========================================================

def interactive_detail_viewer(
    image,
    height=DETAIL_VIEWER_HEIGHT,
):

    if image is None:

        st.info(
            "No image available."
        )

        return


    image_base64 = image_to_base64(
        image
    )


    if not image_base64:

        st.info(
            "Unable to display image."
        )

        return


    viewer_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width,
                 initial-scale=1.0"
    >


    <style>

    * {{
        box-sizing: border-box;
    }}


    html,
    body {{

        margin: 0;
        padding: 0;

        width: 100%;
        height: 100%;

        overflow: hidden;

        background: #111;
    }}


    /* ===================================================
       VIEWER
       =================================================== */

    #viewer {{

        position: relative;

        width: 100%;
        height: {height}px;

        overflow: hidden;

        background: #111;

        border-radius: 10px;

        border:
            1px solid
            rgba(
                255,
                255,
                255,
                0.14
            );

        cursor: grab;

        user-select: none;

        touch-action: none;
    }}


    #viewer.dragging {{

        cursor: grabbing;
    }}


    /* ===================================================
       IMAGE
       =================================================== */

    #photo {{

        position: absolute;

        left: 50%;
        top: 50%;

        display: block;

        max-width: none;
        max-height: none;

        transform-origin:
            center center;

        pointer-events: none;

        user-select: none;

        -webkit-user-drag: none;

        will-change:
            transform;
    }}


    /* ===================================================
       CONTROLS
       =================================================== */

    .controls {{

        position: absolute;

        top: 12px;
        right: 12px;

        z-index: 10;

        display: flex;

        gap: 5px;
    }}


    .control {{

        min-width: 38px;
        height: 38px;

        padding:
            0 10px;

        border: none;

        border-radius: 8px;

        background:
            rgba(
                20,
                20,
                20,
                0.85
            );

        color: white;

        font-size: 18px;

        font-weight: 600;

        cursor: pointer;

        backdrop-filter:
            blur(8px);
    }}


    .control:hover {{

        background:
            rgba(
                55,
                55,
                55,
                0.95
            );
    }}


    .reset {{

        font-size: 12px;
    }}


    /* ===================================================
       ZOOM LABEL
       =================================================== */

    #zoomLabel {{

        position: absolute;

        left: 12px;
        bottom: 12px;

        z-index: 10;

        padding:
            5px 9px;

        border-radius: 6px;

        background:
            rgba(
                20,
                20,
                20,
                0.78
            );

        color:
            rgba(
                255,
                255,
                255,
                0.90
            );

        font-size: 11px;
    }}


    /* ===================================================
       HELP
       =================================================== */

    #help {{

        position: absolute;

        left: 50%;
        bottom: 12px;

        transform:
            translateX(-50%);

        z-index: 10;

        padding:
            5px 10px;

        border-radius: 6px;

        background:
            rgba(
                20,
                20,
                20,
                0.70
            );

        color:
            rgba(
                255,
                255,
                255,
                0.80
            );

        font-size: 11px;

        pointer-events: none;
    }}


    </style>

    </head>


    <body>


    <div
        id="viewer"
    >


        <!-- =========================================
             CONTROLS
             ========================================= -->

        <div
            class="controls"
        >

            <button
                id="zoomOut"
                class="control"
                title="Zoom out"
            >
                −
            </button>


            <button
                id="zoomIn"
                class="control"
                title="Zoom in"
            >
                +
            </button>


            <button
                id="reset"
                class="control reset"
                title="Fit photo"
            >
                Fit
            </button>

        </div>


        <!-- =========================================
             PHOTO
             ========================================= -->

        <img
            id="photo"
            src="data:image/jpeg;base64,{image_base64}"
            draggable="false"
            alt="Leather photo"
        >


        <!-- =========================================
             ZOOM LABEL
             ========================================= -->

        <div id="zoomLabel">
            100%
        </div>


        <!-- =========================================
             HELP
             ========================================= -->

        <div id="help">

            Scroll to zoom
            •
            Drag to move
            •
            Double-click to fit

        </div>


    </div>


    <script>


    // =================================================
    // ELEMENTS
    // =================================================

    const viewer =
        document.getElementById(
            "viewer"
        );


    const photo =
        document.getElementById(
            "photo"
        );


    const zoomLabel =
        document.getElementById(
            "zoomLabel"
        );


    const zoomIn =
        document.getElementById(
            "zoomIn"
        );


    const zoomOut =
        document.getElementById(
            "zoomOut"
        );


    const resetButton =
        document.getElementById(
            "reset"
        );


    // =================================================
    // STATE
    // =================================================

    let baseScale = 1;

    let scale = 1;

    let translateX = 0;

    let translateY = 0;


    let imageWidth = 0;

    let imageHeight = 0;


    let dragging = false;

    let startX = 0;

    let startY = 0;

    let startTranslateX = 0;

    let startTranslateY = 0;


    const MIN_ZOOM = 0.5;

    const MAX_ZOOM = 8;


    // =================================================
    // GET VIEWER SIZE
    // =================================================

    function viewerSize() {{

        return {{
            width:
                viewer.clientWidth,

            height:
                viewer.clientHeight
        }};
    }}


    // =================================================
    // CLAMP PAN
    // =================================================

    function clampPan() {{

        const size =
            viewerSize();


        const renderedWidth =
            imageWidth * scale;


        const renderedHeight =
            imageHeight * scale;


        const maxX =
            Math.max(
                0,
                (
                    renderedWidth -
                    size.width
                ) / 2
            );


        const maxY =
            Math.max(
                0,
                (
                    renderedHeight -
                    size.height
                ) / 2
            );


        translateX =
            Math.max(
                -maxX,
                Math.min(
                    maxX,
                    translateX
                )
            );


        translateY =
            Math.max(
                -maxY,
                Math.min(
                    maxY,
                    translateY
                )
            );
    }}


    // =================================================
    // UPDATE LABEL
    // =================================================

    function updateLabel() {{

        const relativeZoom =
            scale / baseScale;


        zoomLabel.textContent =
            Math.round(
                relativeZoom * 100
            ) + "%";
    }}


    // =================================================
    // APPLY TRANSFORM
    // =================================================

    function applyTransform() {{

        clampPan();


        photo.style.transform =
            "translate(-50%, -50%) " +
            "translate(" +
            translateX +
            "px, " +
            translateY +
            "px) " +
            "scale(" +
            scale +
            ")";


        updateLabel();
    }}


    // =================================================
    // FIT PHOTO
    // =================================================

    function fitPhoto() {{

        const size =
            viewerSize();


        if (
            imageWidth <= 0 ||
            imageHeight <= 0
        ) {{

            return;
        }}


        // IMPORTANT:
        //
        // Fit entire original image
        // inside the viewer.
        //
        // This fixes the previous
        // "already zoomed" problem.

        const widthScale =
            (
                size.width - 20
            ) / imageWidth;


        const heightScale =
            (
                size.height - 20
            ) / imageHeight;


        baseScale =
            Math.min(
                widthScale,
                heightScale
            );


        baseScale =
            Math.max(
                0.01,
                baseScale
            );


        scale =
            baseScale;


        translateX = 0;

        translateY = 0;


        applyTransform();
    }}


    // =================================================
    // ZOOM AROUND CURSOR
    // =================================================

    function zoomAt(
        requestedScale,
        mouseX,
        mouseY
    ) {{

        const oldScale =
            scale;


        const newScale =
            Math.max(
                baseScale * MIN_ZOOM,
                Math.min(
                    baseScale *
                    MAX_ZOOM,
                    requestedScale
                )
            );


        if (
            Math.abs(
                newScale -
                oldScale
            ) < 0.0001
        ) {{

            return;
        }}


        const size =
            viewerSize();


        const centerX =
            size.width / 2;


        const centerY =
            size.height / 2;


        const pointX =
            mouseX -
            centerX;


        const pointY =
            mouseY -
            centerY;


        const ratio =
            newScale /
            oldScale;


        translateX =
            pointX -
            (
                pointX -
                translateX
            ) *
            ratio;


        translateY =
            pointY -
            (
                pointY -
                translateY
            ) *
            ratio;


        scale =
            newScale;


        applyTransform();
    }}


    // =================================================
    // MOUSE WHEEL
    // =================================================

    viewer.addEventListener(
        "wheel",
        function(event) {{

            event.preventDefault();

            event.stopPropagation();


            const rect =
                viewer.getBoundingClientRect();


            const mouseX =
                event.clientX -
                rect.left;


            const mouseY =
                event.clientY -
                rect.top;


            if (
                event.deltaY < 0
            ) {{

                zoomAt(
                    scale * 1.15,
                    mouseX,
                    mouseY
                );

            }} else {{

                zoomAt(
                    scale * 0.87,
                    mouseX,
                    mouseY
                );
            }}

        }},
        {{
            passive: false
        }}
    );


    // =================================================
    // MOUSE DOWN
    // =================================================

    viewer.addEventListener(
        "mousedown",
        function(event) {{

            if (
                event.button !== 0
            ) {{

                return;
            }}


            if (
                event.target.tagName ===
                "BUTTON"
            ) {{

                return;
            }}


            dragging = true;


            viewer.classList.add(
                "dragging"
            );


            startX =
                event.clientX;


            startY =
                event.clientY;


            startTranslateX =
                translateX;


            startTranslateY =
                translateY;


            event.preventDefault();

        }}
    );


    // =================================================
    // MOUSE MOVE
    // =================================================

    window.addEventListener(
        "mousemove",
        function(event) {{

            if (!dragging) {{

                return;
            }}


            translateX =
                startTranslateX +
                (
                    event.clientX -
                    startX
                );


            translateY =
                startTranslateY +
                (
                    event.clientY -
                    startY
                );


            applyTransform();

        }}
    );


    // =================================================
    // MOUSE UP
    // =================================================

    window.addEventListener(
        "mouseup",
        function() {{

            dragging = false;

            viewer.classList.remove(
                "dragging"
            );

        }}
    );


    // =================================================
    // DOUBLE CLICK
    // =================================================

    viewer.addEventListener(
        "dblclick",
        function(event) {{

            if (
                event.target.tagName ===
                "BUTTON"
            ) {{

                return;
            }}


            fitPhoto();

        }}
    );


    // =================================================
    // ZOOM IN
    // =================================================

    zoomIn.addEventListener(
        "click",
        function(event) {{

            event.stopPropagation();


            const size =
                viewerSize();


            zoomAt(
                scale * 1.25,
                size.width / 2,
                size.height / 2
            );

        }}
    );


    // =================================================
    // ZOOM OUT
    // =================================================

    zoomOut.addEventListener(
        "click",
        function(event) {{

            event.stopPropagation();


            const size =
                viewerSize();


            zoomAt(
                scale * 0.8,
                size.width / 2,
                size.height / 2
            );

        }}
    );


    // =================================================
    // FIT BUTTON
    // =================================================

    resetButton.addEventListener(
        "click",
        function(event) {{

            event.stopPropagation();

            fitPhoto();

        }}
    );


    // =================================================
    // TOUCH DRAG
    // =================================================

    let touchStartX = 0;

    let touchStartY = 0;

    let touchStartTranslateX = 0;

    let touchStartTranslateY = 0;


    viewer.addEventListener(
        "touchstart",
        function(event) {{

            if (
                event.touches.length !== 1
            ) {{

                return;
            }}


            const touch =
                event.touches[0];


            touchStartX =
                touch.clientX;


            touchStartY =
                touch.clientY;


            touchStartTranslateX =
                translateX;


            touchStartTranslateY =
                translateY;

        }},
        {{
            passive: true
        }}
    );


    viewer.addEventListener(
        "touchmove",
        function(event) {{

            if (
                event.touches.length !== 1
            ) {{

                return;
            }}


            const touch =
                event.touches[0];


            translateX =
                touch.clientX -
                touchStartX +
                touchStartTranslateX;


            translateY =
                touch.clientY -
                touchStartY +
                touchStartTranslateY;


            applyTransform();


            event.preventDefault();

        }},
        {{
            passive: false
        }}
    );


    // =================================================
    // IMAGE LOADED
    // =================================================

    photo.addEventListener(
        "load",
        function() {{

            imageWidth =
                photo.naturalWidth;


            imageHeight =
                photo.naturalHeight;


            photo.style.width =
                imageWidth + "px";


            photo.style.height =
                imageHeight + "px";


            // THIS IS THE IMPORTANT PART:
            //
            // The first display is FIT TO VIEWER.
            //
            // It does NOT start at 100% native size.

            fitPhoto();

        }}
    );


    // =================================================
    // WINDOW RESIZE
    // =================================================

    window.addEventListener(
        "resize",
        function() {{

            fitPhoto();

        }}
    );


    </script>


    </body>

    </html>
    """


    st.iframe(
        viewer_html,
        height=height,
    )


# =========================================================
# DETAIL INFORMATION
#
# Compact layout so everything fits in the same view.
# =========================================================

def show_detail_information(
    product,
    main_image,
    closeup_image,
):

    leather_id = str(
        product.get("leather_id")
        or "-"
    )

    article_name = str(
        product.get("article_name")
        or "-"
    )

    color = str(
        product.get("color")
        or "-"
    )

    thickness = str(
        product.get("thickness")
        or "-"
    )

    animal = str(
        product.get("animal")
        or "-"
    )

    tannage = str(
        product.get("tannage")
        or "-"
    )

    origin = str(
        product.get("origin")
        or "-"
    )


    st.markdown(
        "### Product Information"
    )


    # =====================================================
    # ROW 1
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )


    with col1:

        st.caption(
            "Leather ID"
        )

        st.write(
            leather_id
        )


    with col2:

        st.caption(
            "Article Name"
        )

        st.write(
            article_name
        )


    # =====================================================
    # ROW 2
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )


    with col1:

        st.caption(
            "Colour"
        )

        st.write(
            color
        )


    with col2:

        st.caption(
            "Thickness"
        )

        st.write(
            thickness
        )


    # =====================================================
    # ROW 3
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )


    with col1:

        st.caption(
            "Animal"
        )

        st.write(
            animal
        )


    with col2:

        st.caption(
            "Tannage"
        )

        st.write(
            tannage
        )


    # =====================================================
    # ROW 4
    # =====================================================

    col1, col2 = st.columns(
        2,
        gap="medium",
    )


    with col1:

        st.caption(
            "Origin"
        )

        st.write(
            origin
        )


    with col2:

        st.caption(
            "Photos"
        )

        if (
            main_image is not None
            and closeup_image is not None
        ):

            st.write(
                "Main + Close-up"
            )

        elif main_image is not None:

            st.write(
                "Main only"
            )

        elif closeup_image is not None:

            st.write(
                "Close-up only"
            )

        else:

            st.write(
                "No photos"
            )


# =========================================================
# DETAIL DIALOG
# =========================================================

@st.dialog(
    "Leather Details",
    width="large",
    dismissible=True,
)
def show_product_details(product):

    leather_id = str(
        product.get("leather_id")
        or "-"
    )

    article_name = str(
        product.get("article_name")
        or "-"
    )


    main_url = get_image_url(
        product.get("main_photo")
    )


    closeup_url = get_image_url(
        product.get("closeup_photo")
    )


    # =====================================================
    # LOAD ORIGINAL IMAGES
    # =====================================================

    main_image = (
        load_image(main_url)
        if main_url
        else None
    )


    closeup_image = (
        load_image(closeup_url)
        if closeup_url
        else None
    )


    # =====================================================
    # PHOTO OPTIONS
    # =====================================================

    photo_options = []


    if main_image is not None:

        photo_options.append(
            "Main"
        )


    if closeup_image is not None:

        photo_options.append(
            "Close-up"
        )


    # =====================================================
    # PHOTO SELECTOR
    # =====================================================

    if len(photo_options) == 2:

        selected_photo = (
            st.segmented_control(
                "Photo",
                photo_options,
                default="Main",
                width="stretch",
                key=(
                    f"detail_photo_"
                    f"{leather_id}"
                ),
            )
        )

    elif len(photo_options) == 1:

        selected_photo = (
            photo_options[0]
        )

    else:

        selected_photo = None


    # =====================================================
    # SELECT CURRENT IMAGE
    # =====================================================

    if selected_photo == "Close-up":

        selected_image = (
            closeup_image
        )

    else:

        selected_image = (
            main_image
        )


    # =====================================================
    # MAIN DIALOG LAYOUT
    #
    # Photo = left
    # Information = right
    # =====================================================

    photo_col, details_col = (
        st.columns(
            [1.65, 1],
            gap="large",
        )
    )


    # =====================================================
    # PHOTO
    # =====================================================

    with photo_col:

        st.markdown(
            f"### {article_name}"
        )


        if selected_image is None:

            st.info(
                "No image available."
            )

        else:

            interactive_detail_viewer(
                selected_image,
                height=DETAIL_VIEWER_HEIGHT,
            )


            st.caption(
                "Scroll to zoom • "
                "Drag to move • "
                "Double-click or Fit to reset"
            )


    # =====================================================
    # INFORMATION
    # =====================================================

    with details_col:

        show_detail_information(
            product,
            main_image,
            closeup_image,
        )


# =========================================================
# HEADER
# =========================================================

st.title(
    "Leather Catalogue"
)

st.caption(
    "Explore our leather collection by article, "
    "colour, animal, tannage and origin."
)


# =========================================================
# SEARCH
# =========================================================

search_col, refresh_col = st.columns(
    [12, 1],
    vertical_alignment="center",
)


with search_col:

    search_text = st.text_input(
        "Search",
        placeholder=(
            "Search leather ID, article, colour, "
            "animal, tannage or origin..."
        ),
        label_visibility="collapsed",
    )


with refresh_col:

    if st.button(
        "↻",
        width="stretch",
        help="Refresh catalogue",
    ):

        st.cache_data.clear()

        st.rerun()


st.divider()


# =========================================================
# FILTER VALUES
# =========================================================

animals = sorted(
    {
        str(
            p["animal"]
        ).strip()

        for p in products

        if p.get("animal")
    }
)


tannages = sorted(
    {
        str(
            p["tannage"]
        ).strip()

        for p in products

        if p.get("tannage")
    }
)


colors = sorted(
    {
        str(
            p["color"]
        ).strip()

        for p in products

        if p.get("color")
    }
)


origins = sorted(
    {
        str(
            p["origin"]
        ).strip()

        for p in products

        if p.get("origin")
    }
)


# =========================================================
# MAIN LAYOUT
# =========================================================

filter_col, catalogue_col = (
    st.columns(
        [1.2, 5],
        gap="large",
    )
)


# =========================================================
# FILTER PANEL
# =========================================================

with filter_col:

    with st.container(
        border=True
    ):

        st.subheader(
            "Filter"
        )

        st.caption(
            "Narrow down the leather collection."
        )


        selected_animals = (
            st.multiselect(
                "Animal",
                options=animals,
                placeholder="All animals",
            )
        )


        selected_tannages = (
            st.multiselect(
                "Tannage",
                options=tannages,
                placeholder="All tannages",
            )
        )


        selected_colors = (
            st.multiselect(
                "Colour",
                options=colors,
                placeholder="All colours",
            )
        )


        selected_origins = (
            st.multiselect(
                "Origin",
                options=origins,
                placeholder="All origins",
            )
        )


        st.divider()


        st.caption(
            f"{len(products)} "
            f"total leather articles"
        )


# =========================================================
# FILTER PRODUCTS
# =========================================================

filtered_products = []


search_lower = (
    search_text
    .strip()
    .lower()
)


for product in products:

    searchable_text = " ".join(
        [
            str(
                product.get(
                    "leather_id"
                )
                or ""
            ),

            str(
                product.get(
                    "article_name"
                )
                or ""
            ),

            str(
                product.get(
                    "color"
                )
                or ""
            ),

            str(
                product.get(
                    "thickness"
                )
                or ""
            ),

            str(
                product.get(
                    "tannage"
                )
                or ""
            ),

            str(
                product.get(
                    "animal"
                )
                or ""
            ),

            str(
                product.get(
                    "origin"
                )
                or ""
            ),
        ]
    ).lower()


    if (
        search_lower
        and search_lower
        not in searchable_text
    ):

        continue


    if selected_animals:

        if (
            product.get("animal")
            not in selected_animals
        ):

            continue


    if selected_tannages:

        if (
            product.get("tannage")
            not in selected_tannages
        ):

            continue


    if selected_colors:

        if (
            product.get("color")
            not in selected_colors
        ):

            continue


    if selected_origins:

        if (
            product.get("origin")
            not in selected_origins
        ):

            continue


    filtered_products.append(
        product
    )


# =========================================================
# CATALOGUE HEADER
# =========================================================

with catalogue_col:

    result_col, sort_col = (
        st.columns(
            [4, 1],
            vertical_alignment="center",
        )
    )


    with result_col:

        st.subheader(
            "Available Leather"
        )

        st.caption(
            f"Showing "
            f"{len(filtered_products)} "
            f"of "
            f"{len(products)} "
            f"leather articles"
        )


    with sort_col:

        sort_option = st.selectbox(
            "Sort",
            [
                "Leather ID",
                "Article",
                "Animal",
                "Colour",
            ],
            label_visibility="collapsed",
        )


# =========================================================
# SORT
# =========================================================

if sort_option == "Leather ID":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "leather_id"
            )
            or ""
        )
    )


elif sort_option == "Article":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "article_name"
            )
            or ""
        ).lower()
    )


elif sort_option == "Animal":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "animal"
            )
            or ""
        ).lower()
    )


elif sort_option == "Colour":

    filtered_products.sort(
        key=lambda x: str(
            x.get(
                "color"
            )
            or ""
        ).lower()
    )


# =========================================================
# EMPTY RESULT
# =========================================================

if not filtered_products:

    with catalogue_col:

        with st.container(
            border=True
        ):

            st.info(
                "No leather articles match "
                "your search or filters."
            )

            st.write(
                "Try clearing one or more filters."
            )

    st.stop()


# =========================================================
# PRODUCT GRID
# =========================================================

with catalogue_col:

    for row_start in range(
        0,
        len(filtered_products),
        4,
    ):

        row_products = (
            filtered_products[
                row_start:
                row_start + 4
            ]
        )


        columns = st.columns(
            4,
            gap="medium",
        )


        for column, product in zip(
            columns,
            row_products,
        ):

            with column:

                with st.container(
                    border=True
                ):

                    # =====================================
                    # IMAGE URLs
                    # =====================================

                    main_url = (
                        get_image_url(
                            product.get(
                                "main_photo"
                            )
                        )
                    )


                    closeup_url = (
                        get_image_url(
                            product.get(
                                "closeup_photo"
                            )
                        )
                    )


                    # =====================================
                    # AUTO-SLIDING IMAGE
                    #
                    # MAIN
                    #   ↓ 5 sec
                    # CLOSE-UP
                    #   ↓ 5 sec
                    # MAIN
                    # =====================================

                    if (
                        main_url
                        or closeup_url
                    ):

                        auto_slide_image(
                            main_url,
                            closeup_url,
                            height=220,
                            key=str(
                                product.get(
                                    "leather_id"
                                )
                            ),
                        )

                    else:

                        st.info(
                            "Image unavailable"
                        )


                    # =====================================
                    # ARTICLE NAME
                    # =====================================

                    st.markdown(
                        f"**{product.get('article_name', '-') }**"
                    )


                    # =====================================
                    # LEATHER ID
                    # =====================================

                    st.caption(
                        "Leather ID: "
                        f"{product.get('leather_id', '-')}"
                    )


                    # =====================================
                    # DETAILS BUTTON
                    # =====================================

                    if st.button(
                        "View details",
                        key=(
                            "details_"
                            f"{product.get('leather_id')}"
                        ),
                        width="stretch",
                        icon=":material/zoom_in:",
                    ):

                        show_product_details(
                            product
                        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Bhartiya Fashions • Leather Catalogue"
)


need to add admin access here also. this all are confidential

Yes. Since the catalogue contains confidential leather information, I recommend not putting the admin CRUD logic directly into this catalogue page.

Your existing admin code already has the correct separation: it uses SUPABASE_SERVICE_ROLE_KEY, while the catalogue uses the normal SUPABASE_KEY.

Recommended structure
your_project/
│
├── app.py                  ← Customer catalogue
│
└── pages/
    └── 1_⚙️_Admin.py      ← Password-protected CRUD

The important security architecture is:

CUSTOMER
   │
   ▼
app.py
   │
   └── SUPABASE_KEY
       ↓
   Read active products only


ADMIN
   │
   ▼
1_⚙️_Admin.py
   │
   ├── ADMIN_PASSWORD
   │
   └── SUPABASE_SERVICE_ROLE_KEY
       ↓
   Add / Edit / Delete / Activate / Deactivate

Your admin page already checks the admin password before allowing access.

1. Add an Admin button to your catalogue

In your current catalogue, find this section:

# =========================================================
# HEADER
# =========================================================

st.title(
    "Leather Catalogue"
)

st.caption(
    "Explore our leather collection by article, "
    "colour, animal, tannage and origin."
)

Replace it with:

# =========================================================
# HEADER
# =========================================================

header_col, admin_col = st.columns(
    [8, 1],
    vertical_alignment="center",
)

with header_col:

    st.title(
        "Leather Catalogue"
    )

    st.caption(
        "Explore our leather collection by article, "
        "colour, animal, tannage and origin."
    )

with admin_col:

    st.page_link(
        "pages/1_⚙️_Admin.py",
        label="Admin",
        icon=":material/admin_panel_settings:",
    )

This gives you:

Leather Catalogue                              [⚙ Admin]
Explore our leather collection...

The important point is that clicking Admin does not give access to CRUD. It only opens the admin page.

The admin page then requires the password.

2. Keep your admin page password protection

Your existing admin code has this:

def check_admin_password():

    if st.session_state.get(
        "admin_authenticated",
        False,
    ):
        return True

and then checks:

admin_password = st.secrets.get(
    "ADMIN_PASSWORD"
)

if password == admin_password:

    st.session_state[
        "admin_authenticated"
    ] = True

    st.rerun()

That is the correct basic pattern.

I would make one improvement: use a session-specific authentication state, and don't expose anything from the admin page until authentication succeeds.

3. Your Streamlit secrets

Your .streamlit/secrets.toml should contain:

SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"

SUPABASE_KEY = "your-publishable-or-anon-key"

SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"

ADMIN_PASSWORD = "your-very-strong-admin-password"
Very important

Do not put this:

SUPABASE_SERVICE_ROLE_KEY

inside the customer catalogue code.

Your catalogue should continue using:

return create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)

Your admin page should use:

return create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
)

Your existing admin implementation already follows this separation.

4. One more important security issue

Because you said:

"this all are confidential"

there is a distinction between hiding the admin page and protecting the catalogue data.

Your current catalogue does:

.eq("is_active", True)

so it only loads active products.

That's good for the application interface.

But if the Supabase table/storage has permissive public policies, someone could potentially access the Supabase endpoint directly without using your Streamlit UI.

So I recommend this final architecture:

Supabase
leather_products
        │
        ├── Customer:
        │      SELECT active products only
        │
        └── Admin:
               service role
               INSERT
               UPDATE
               DELETE
Storage
leather-images
        │
        ├── Customer → only images needed by catalogue
        │
        └── Admin → upload/delete

Your admin code uploads images using the storage client and deletes them when required.

5. I also recommend changing the Admin link slightly

If you don't want customers to even see an obvious "Admin" button, put it in the sidebar:

with st.sidebar:

    st.markdown("### Catalogue")

    st.page_link(
        "app.py",
        label="Leather Catalogue",
        icon=":material/menu_book:",
    )

    st.divider()

    st.page_link(
        "pages/1_⚙️_Admin.py",
        label="Admin",
        icon=":material/admin_panel_settings:",
    )

But hiding the button is not security. The admin page must still enforce the password, which yours does.

6. I would make your admin page more secure

Your current password comparison is:

if password == admin_password:

For a small internal business application, this is workable, but I would improve it to:

import hmac

and:

if hmac.compare_digest(
    password,
    admin_password,
):
    st.session_state["admin_authenticated"] = True
    st.rerun()
else:
    st.error("Incorrect password.")

This avoids a normal string comparison for the password.

7. Add logout

Your admin code already has logout:

if st.button(
    "Logout",
    width="stretch",
):

    st.session_state[
        "admin_authenticated"
    ] = False

    st.rerun()

That's good.

8. One important improvement to your current CRUD

Your duplicate checking currently happens in Python:

for product in load_all_products():

and checks:

if existing_id.casefold() == lid:

and:

if existing_name.casefold() == name:

Your current admin code therefore intends both Leather ID and Article Name to be unique, case-insensitively.

However, for real data protection, I recommend also enforcing uniqueness inside PostgreSQL/Supabase.

Otherwise two simultaneous admin operations could theoretically bypass the Python check.

For example, ultimately the database should enforce uniqueness on:

leather_id
article_name

Then your application validation is just the user-friendly first layer.

What I recommend for your website

I would make the final project:

Leather Catalogue
│
├── 🧥 Catalogue
│   │
│   ├── Search
│   ├── Animal filter
│   ├── Tannage filter
│   ├── Colour filter
│   ├── Origin filter
│   ├── Auto main/close-up photos
│   └── Interactive photo viewer
│
└── ⚙️ Admin
    │
    ├── 🔐 Password login
    │
    ├── ➕ Add Leather
    │   ├── Leather ID
    │   ├── Article Name
    │   ├── Colour
    │   ├── Thickness
    │   ├── Animal
    │   ├── Tannage
    │   ├── Origin
    │   ├── Main Photo
    │   └── Close-up Photo
    │
    └── 📋 Manage Catalogue
        ├── Search
        ├── Edit
        ├── Replace photos
        ├── Activate
        ├── Deactivate
        └── Permanently delete

Your existing admin implementation already contains essentially all of the CRUD functionality needed.

Most importantly: don't put the service-role key into the catalogue page. Keep it exclusively in the password-protected admin page.

If you want the 
entire current app.py rewritten with the Admin access integrated + the complete corrected 1_⚙️_Admin.py + Supabase RLS/storage policies, I can give you the complete project files rather than asking you to manually merge pieces.

need cataloge page with admin access passowrd protected
 full code

Yes. Since your catalogue data is confidential, I recommend keeping one customer catalogue page with a clearly separated password-protected Admin section.

The code below keeps:

Customer catalogue
Search/filter/sort
Product cards
Main + close-up image viewer
Product detail dialog
Admin password login
Add leather
Edit leather
Activate/deactivate
Delete leather
Add/replace/delete photos
Case-insensitive duplicate checking for Leather ID and Article Name
Supabase service-role key only used server-side
Logout
Refresh
No hard-coded passwords or Supabase secrets

Your existing admin implementation already uses leather_products and leather-images, and its admin connection is based on SUPABASE_SERVICE_ROLE_KEY. The uploaded admin code also already has password authentication and logout logic.

1. app.py

Replace your current app.py with this complete version:

import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
from PIL import Image
import uuid
import hmac
import html
import base64
import json


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="🧥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONSTANTS
# ============================================================

TABLE_NAME = "leather_products"
BUCKET_NAME = "leather-images"

IMAGE_TYPES = [
    "jpg",
    "jpeg",
    "png",
    "webp",
]


# ============================================================
# SESSION STATE
# ============================================================

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "admin_login_error" not in st.session_state:
    st.session_state.admin_login_error = False


# ============================================================
# SUPABASE - CUSTOMER CONNECTION
# ============================================================

@st.cache_resource
def get_customer_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


# ============================================================
# SUPABASE - ADMIN CONNECTION
# ============================================================

@st.cache_resource
def get_admin_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )


# ============================================================
# CUSTOMER SUPABASE
# ============================================================

try:

    customer_supabase = get_customer_supabase()

except Exception as e:

    st.error("Unable to connect to the catalogue database.")

    st.info(
        "Please check SUPABASE_URL and SUPABASE_KEY "
        "in Streamlit secrets."
    )

    st.exception(e)

    st.stop()


# ============================================================
# IMAGE URL
# ============================================================

def get_image_url(filename):

    if not filename:
        return None

    filename = str(filename).strip()

    if not filename:
        return None

    return (
        f"{st.secrets['SUPABASE_URL']}"
        f"/storage/v1/object/public/"
        f"{BUCKET_NAME}/"
        f"{quote(filename)}"
    )


# ============================================================
# LOAD IMAGE
# ============================================================

@st.cache_data(
    ttl=600,
    show_spinner=False,
)
def load_image(image_url):

    if not image_url:
        return None

    try:

        with urlopen(
            image_url,
            timeout=20,
        ) as response:

            image_bytes = response.read()

        return Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

    except Exception:

        return None


# ============================================================
# LOAD ACTIVE PRODUCTS
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def load_products():

    response = (
        customer_supabase
        .table(TABLE_NAME)
        .select(
            """
            leather_id,
            article_name,
            color,
            thickness,
            tannage,
            animal,
            origin,
            main_photo,
            closeup_photo,
            is_active
            """
        )
        .eq(
            "is_active",
            True,
        )
        .order(
            "leather_id"
        )
        .execute()
    )

    return response.data or []


# ============================================================
# ADMIN PASSWORD
# ============================================================

def check_admin_password():

    if st.session_state.admin_authenticated:
        return True

    st.markdown(
        """
        <div style="
            max-width:500px;
            margin:40px auto 20px auto;
            padding:30px;
            border-radius:16px;
            border:1px solid rgba(128,128,128,0.25);
        ">
            <h2 style="text-align:center;">
                🔐 Catalogue Administration
            </h2>
            <p style="
                text-align:center;
                opacity:0.7;
            ">
                Restricted access
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input(
        "Admin Password",
        type="password",
        placeholder="Enter admin password",
        key="admin_password_input",
    )

    if st.button(
        "Login",
        type="primary",
        width="stretch",
        key="admin_login_button",
    ):

        configured_password = st.secrets.get(
            "ADMIN_PASSWORD"
        )

        if not configured_password:

            st.error(
                "ADMIN_PASSWORD is not configured "
                "in Streamlit secrets."
            )

            return False

        if hmac.compare_digest(
            password,
            str(configured_password),
        ):

            st.session_state.admin_authenticated = True
            st.session_state.admin_login_error = False

            st.rerun()

        else:

            st.session_state.admin_login_error = True
            st.error("Incorrect admin password.")

    return False


# ============================================================
# ADMIN CONNECTION
# ============================================================

def get_admin_client():

    try:

        return get_admin_supabase()

    except Exception as e:

        st.error(
            "Admin database connection could not be established."
        )

        st.exception(e)

        return None


# ============================================================
# LOAD ALL PRODUCTS - ADMIN
# ============================================================

@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_all_products():

    admin_supabase = get_admin_supabase()

    response = (
        admin_supabase
        .table(TABLE_NAME)
        .select(
            """
            leather_id,
            article_name,
            color,
            thickness,
            tannage,
            animal,
            origin,
            main_photo,
            closeup_photo,
            is_active
            """
        )
        .order(
            "leather_id"
        )
        .execute()
    )

    return response.data or []


# ============================================================
# DUPLICATE CHECK
# ============================================================

def check_duplicate_product(
    leather_id,
    article_name,
    exclude_leather_id=None,
):

    leather_id = str(
        leather_id or ""
    ).strip().casefold()

    article_name = str(
        article_name or ""
    ).strip().casefold()

    exclude_id = None

    if exclude_leather_id:
        exclude_id = str(
            exclude_leather_id
        ).strip().casefold()

    for product in load_all_products():

        existing_id = str(
            product.get("leather_id") or ""
        ).strip()

        existing_name = str(
            product.get("article_name") or ""
        ).strip()

        if (
            exclude_id
            and existing_id.casefold() == exclude_id
        ):
            continue

        if existing_id.casefold() == leather_id:

            return (
                False,
                f"Leather ID '{leather_id}' already exists.",
            )

        if existing_name.casefold() == article_name:

            return (
                False,
                f"Article Name '{article_name}' already exists.",
            )

    return True, ""


# ============================================================
# STORAGE - UPLOAD
# ============================================================

def upload_image(
    uploaded_file,
    leather_id,
    photo_type,
):

    if uploaded_file is None:
        return None

    original_name = (
        uploaded_file.name
        or "image.jpg"
    )

    if "." in original_name:

        extension = (
            original_name
            .rsplit(".", 1)[-1]
            .lower()
        )

    else:

        extension = "jpg"

    if extension not in IMAGE_TYPES:
        extension = "jpg"

    unique_id = uuid.uuid4().hex[:10]

    safe_leather_id = (
        str(leather_id)
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    filename = (
        f"{safe_leather_id}_"
        f"{photo_type}_"
        f"{unique_id}."
        f"{extension}"
    )

    try:

        admin_supabase = get_admin_supabase()

        admin_supabase.storage.from_(
            BUCKET_NAME
        ).upload(
            filename,
            uploaded_file.getvalue(),
            {
                "content-type": (
                    uploaded_file.type
                    or "image/jpeg"
                ),
                "upsert": False,
            },
        )

        return filename

    except Exception as e:

        st.error(
            f"Unable to upload {photo_type} photo."
        )

        st.exception(e)

        return None


# ============================================================
# STORAGE - DELETE
# ============================================================

def delete_storage_file(filename):

    if not filename:
        return True

    try:

        admin_supabase = get_admin_supabase()

        admin_supabase.storage.from_(
            BUCKET_NAME
        ).remove(
            [filename]
        )

        return True

    except Exception as e:

        st.warning(
            f"Could not delete storage file: {filename}"
        )

        st.caption(str(e))

        return False


# ============================================================
# CREATE PRODUCT
# ============================================================

def create_product(
    leather_id,
    article_name,
    color,
    thickness,
    tannage,
    animal,
    origin,
    main_photo,
    closeup_photo,
    is_active,
):

    admin_supabase = get_admin_supabase()

    return (
        admin_supabase
        .table(TABLE_NAME)
        .insert(
            {
                "leather_id": leather_id,
                "article_name": article_name,
                "color": color,
                "thickness": thickness,
                "tannage": tannage,
                "animal": animal,
                "origin": origin,
                "main_photo": main_photo,
                "closeup_photo": closeup_photo,
                "is_active": is_active,
            }
        )
        .execute()
    )


# ============================================================
# UPDATE PRODUCT
# ============================================================

def update_product(
    leather_id,
    article_name,
    color,
    thickness,
    tannage,
    animal,
    origin,
    main_photo,
    closeup_photo,
    is_active,
):

    admin_supabase = get_admin_supabase()

    return (
        admin_supabase
        .table(TABLE_NAME)
        .update(
            {
                "article_name": article_name,
                "color": color,
                "thickness": thickness,
                "tannage": tannage,
                "animal": animal,
                "origin": origin,
                "main_photo": main_photo,
                "closeup_photo": closeup_photo,
                "is_active": is_active,
            }
        )
        .eq(
            "leather_id",
            leather_id,
        )
        .execute()
    )


# ============================================================
# DELETE PRODUCT
# ============================================================

def delete_product(product):

    leather_id = product.get(
        "leather_id"
    )

    main_photo = product.get(
        "main_photo"
    )

    closeup_photo = product.get(
        "closeup_photo"
    )

    try:

        admin_supabase = get_admin_supabase()

        # Delete database record first
        (
            admin_supabase
            .table(TABLE_NAME)
            .delete()
            .eq(
                "leather_id",
                leather_id,
            )
            .execute()
        )

        # Then delete storage files
        if main_photo:

            delete_storage_file(
                main_photo
            )

        if (
            closeup_photo
            and closeup_photo != main_photo
        ):

            delete_storage_file(
                closeup_photo
            )

        return True

    except Exception as e:

        st.error(
            "Unable to delete leather article."
        )

        st.exception(e)

        return False


# ============================================================
# CUSTOMER IMAGE SLIDER
# ============================================================

def render_image_slider(
    main_url,
    closeup_url,
    height=350,
):

    images = [
        url
        for url in [
            main_url,
            closeup_url,
        ]
        if url
    ]

    if not images:
        return

    encoded_images = []

    for image_url in images:

        encoded_images.append(
            json.dumps(image_url)
        )

    images_json = "[" + ",".join(
        encoded_images
    ) + "]"

    slider_html = f"""
    <div style="
        width:100%;
        height:{height}px;
        overflow:hidden;
        border-radius:12px;
        background:#f5f5f5;
        position:relative;
    ">

        <img
            id="catalogue-slide-image"
            src={json.dumps(images[0])}
            style="
                width:100%;
                height:100%;
                object-fit:cover;
                display:block;
            "
        />

    </div>

    <script>

        const catalogueImages = {images_json};

        let catalogueIndex = 0;

        const catalogueImage =
            document.getElementById(
                "catalogue-slide-image"
            );

        if (catalogueImages.length > 1) {{

            setInterval(function() {{

                catalogueIndex =
                    (catalogueIndex + 1)
                    % catalogueImages.length;

                catalogueImage.src =
                    catalogueImages[catalogueIndex];

            }}, 5000);

        }}

    </script>
    """

    st.components.v1.html(
        slider_html,
        height=height + 10,
    )


# ============================================================
# DETAIL IMAGE VIEWER
# ============================================================

def render_detail_image(
    image_url,
    key,
):

    if not image_url:
        st.info("No image available.")
        return

    image = load_image(image_url)

    if image is None:

        st.image(
            image_url,
            width="stretch",
        )

        return

    buffered = BytesIO()

    image.save(
        buffered,
        format="JPEG",
        quality=90,
    )

    image_base64 = base64.b64encode(
        buffered.getvalue()
    ).decode()

    viewer_html = f"""
    <div style="
        width:100%;
        height:550px;
        overflow:hidden;
        position:relative;
        border-radius:12px;
        background:#f5f5f5;
        cursor:grab;
    ">

        <img
            id="zoom-image-{key}"
            src="data:image/jpeg;base64,{image_base64}"
            style="
                max-width:none;
                width:100%;
                height:100%;
                object-fit:contain;
                transform-origin:center center;
                user-select:none;
                transition:transform 0.08s;
            "
        />

    </div>

    <script>

        const image =
            document.getElementById(
                "zoom-image-{key}"
            );

        let scale = 1;
        let posX = 0;
        let posY = 0;

        let dragging = false;
        let startX = 0;
        let startY = 0;

        function updateImage() {{

            image.style.transform =
                `translate(${{posX}}px, ${{posY}}px)
                 scale(${{scale}})`;

        }}

        image.parentElement.addEventListener(
            "wheel",
            function(event) {{

                event.preventDefault();

                if (event.deltaY < 0) {{
                    scale += 0.15;
                }} else {{
                    scale -= 0.15;
                }}

                scale = Math.max(
                    1,
                    Math.min(5, scale)
                );

                updateImage();

            }},
            {{ passive:false }}
        );

        image.parentElement.addEventListener(
            "mousedown",
            function(event) {{

                dragging = true;

                startX = event.clientX - posX;
                startY = event.clientY - posY;

                image.parentElement.style.cursor =
                    "grabbing";

            }}
        );

        window.addEventListener(
            "mouseup",
            function() {{

                dragging = false;

                image.parentElement.style.cursor =
                    "grab";

            }}
        );

        window.addEventListener(
            "mousemove",
            function(event) {{

                if (!dragging) return;

                posX =
                    event.clientX - startX;

                posY =
                    event.clientY - startY;

                updateImage();

            }}
        );

    </script>
    """

    st.components.v1.html(
        viewer_html,
        height=560,
    )


# ============================================================
# PRODUCT DETAIL
# ============================================================

@st.dialog("Leather Details", width="large")
def show_product_details(product):

    leather_id = product.get(
        "leather_id"
    )

    article_name = product.get(
        "article_name"
    )

    main_photo = product.get(
        "main_photo"
    )

    closeup_photo = product.get(
        "closeup_photo"
    )

    main_url = get_image_url(
        main_photo
    )

    closeup_url = get_image_url(
        closeup_photo
    )

    st.subheader(
        article_name or "-"
    )

    st.caption(
        f"Leather ID: {leather_id or '-'}"
    )

    image_options = []

    if main_url:
        image_options.append(
            ("Main Photo", main_url)
        )

    if closeup_url:
        image_options.append(
            ("Close-up Photo", closeup_url)
        )

    if image_options:

        selected_image = st.selectbox(
            "View Image",
            options=[
                item[0]
                for item in image_options
            ],
            key=f"detail_image_{leather_id}",
        )

        selected_url = dict(
            image_options
        )[selected_image]

        render_detail_image(
            selected_url,
            key=str(leather_id).replace(
                " ",
                "_",
            ),
        )

    else:

        st.info(
            "No photos available for this article."
        )

    st.divider()

    info_col1, info_col2 = st.columns(2)

    with info_col1:

        st.markdown(
            f"**Colour**  \n"
            f"{product.get('color') or '-'}"
        )

        st.markdown(
            f"**Thickness**  \n"
            f"{product.get('thickness') or '-'}"
        )

        st.markdown(
            f"**Animal**  \n"
            f"{product.get('animal') or '-'}"
        )

    with info_col2:

        st.markdown(
            f"**Tannage**  \n"
            f"{product.get('tannage') or '-'}"
        )

        st.markdown(
            f"**Origin**  \n"
            f"{product.get('origin') or '-'}"
        )

        st.markdown(
            f"**Article Name**  \n"
            f"{article_name or '-'}"
        )


# ============================================================
# ADMIN PANEL
# ============================================================

def render_admin_panel():

    st.markdown(
        """
        <div style="
            padding:18px 22px;
            border-radius:14px;
            background:rgba(128,128,128,0.08);
            border:1px solid rgba(128,128,128,0.20);
            margin-bottom:20px;
        ">
            <h2 style="margin:0;">
                ⚙️ Catalogue Administration
            </h2>
            <p style="margin:5px 0 0 0; opacity:0.7;">
                Restricted catalogue management
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    header_col, logout_col = st.columns(
        [8, 1],
        vertical_alignment="center",
    )

    with header_col:

        st.caption(
            "Add, edit, activate, deactivate and "
            "delete leather catalogue articles."
        )

    with logout_col:

        if st.button(
            "Logout",
            width="stretch",
            key="admin_logout",
        ):

            st.session_state.admin_authenticated = False

            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # LOAD PRODUCTS
    # --------------------------------------------------------

    try:

        products = load_all_products()

    except Exception as e:

        st.error(
            "Unable to load catalogue."
        )

        st.exception(e)

        return

    refresh_col, status_col = st.columns(
        [1, 5],
        vertical_alignment="center",
    )

    with refresh_col:

        if st.button(
            "↻ Refresh",
            width="stretch",
            key="admin_refresh",
        ):

            st.cache_data.clear()

            st.rerun()

    with status_col:

        active_count = sum(
            bool(
                p.get("is_active")
            )
            for p in products
        )

        inactive_count = (
            len(products)
            - active_count
        )

        st.info(
            f"Total: {len(products)}  |  "
            f"Active: {active_count}  |  "
            f"Inactive: {inactive_count}"
        )

    st.divider()

    tab_add, tab_manage = st.tabs(
        [
            "➕ Add Leather",
            "📋 Manage Catalogue",
        ]
    )

    # ========================================================
    # ADD LEATHER
    # ========================================================

    with tab_add:

        st.subheader(
            "Add New Leather Article"
        )

        with st.form(
            "admin_add_product_form",
            clear_on_submit=False,
        ):

            col1, col2 = st.columns(
                2,
                gap="large",
            )

            with col1:

                leather_id = st.text_input(
                    "Leather ID *",
                    placeholder="Example: BIL00021",
                )

                article_name = st.text_input(
                    "Article Name *",
                    placeholder="Example: Cow Lionel",
                )

                color = st.text_input(
                    "Colour",
                    placeholder="Example: Golden Spice",
                )

                thickness = st.text_input(
                    "Thickness",
                    placeholder="Example: 0.7 - 0.8 mm",
                )

            with col2:

                animal = st.text_input(
                    "Animal",
                    placeholder="Example: Cow",
                )

                tannage = st.text_input(
                    "Tannage",
                    placeholder="Example: Semi Veg",
                )

                origin = st.text_input(
                    "Origin",
                    placeholder="Example: Turkey",
                )

                is_active = st.checkbox(
                    "Show in customer catalogue",
                    value=True,
                )

            st.divider()

            photo_col1, photo_col2 = st.columns(
                2,
                gap="large",
            )

            with photo_col1:

                main_photo_file = st.file_uploader(
                    "Main Photo",
                    type=IMAGE_TYPES,
                    key="add_main_photo",
                )

                if main_photo_file:

                    st.image(
                        main_photo_file,
                        caption="Main Photo Preview",
                        width="stretch",
                    )

            with photo_col2:

                closeup_photo_file = st.file_uploader(
                    "Close-up Photo",
                    type=IMAGE_TYPES,
                    key="add_closeup_photo",
                )

                if closeup_photo_file:

                    st.image(
                        closeup_photo_file,
                        caption="Close-up Photo Preview",
                        width="stretch",
                    )

            submitted = st.form_submit_button(
                "➕ Add Leather Article",
                type="primary",
                width="stretch",
            )

        if submitted:

            leather_id = leather_id.strip()
            article_name = article_name.strip()

            if not leather_id:

                st.error(
                    "Leather ID is required."
                )

            elif not article_name:

                st.error(
                    "Article Name is required."
                )

            else:

                valid, message = (
                    check_duplicate_product(
                        leather_id,
                        article_name,
                    )
                )

                if not valid:

                    st.error(message)

                else:

                    main_photo_name = None
                    closeup_photo_name = None

                    with st.spinner(
                        "Creating leather article..."
                    ):

                        # Upload main image
                        if main_photo_file:

                            main_photo_name = upload_image(
                                main_photo_file,
                                leather_id,
                                "main",
                            )

                            if not main_photo_name:

                                st.stop()

                        # Upload close-up
                        if closeup_photo_file:

                            closeup_photo_name = upload_image(
                                closeup_photo_file,
                                leather_id,
                                "closeup",
                            )

                            if not closeup_photo_name:

                                if main_photo_name:
                                    delete_storage_file(
                                        main_photo_name
                                    )

                                st.stop()

                        try:

                            create_product(
                                leather_id=leather_id,
                                article_name=article_name,
                                color=color.strip(),
                                thickness=thickness.strip(),
                                tannage=tannage.strip(),
                                animal=animal.strip(),
                                origin=origin.strip(),
                                main_photo=main_photo_name,
                                closeup_photo=closeup_photo_name,
                                is_active=is_active,
                            )

                            st.cache_data.clear()

                            st.success(
                                f"{leather_id} "
                                "was added successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            if main_photo_name:
                                delete_storage_file(
                                    main_photo_name
                                )

                            if closeup_photo_name:
                                delete_storage_file(
                                    closeup_photo_name
                                )

                            st.error(
                                "Unable to create "
                                "the leather article."
                            )

                            st.exception(e)

    # ========================================================
    # MANAGE CATALOGUE
    # ========================================================

    with tab_manage:

        st.subheader(
            "Manage Existing Articles"
        )

        search_text = st.text_input(
            "Search catalogue",
            placeholder=(
                "Search Leather ID, article, colour, "
                "animal, tannage or origin..."
            ),
            key="admin_search",
        )

        search_lower = (
            search_text
            .strip()
            .casefold()
        )

        filtered_products = []

        for product in products:

            searchable_text = " ".join(
                [
                    str(
                        product.get(
                            "leather_id"
                        )
                        or ""
                    ),

                    str(
                        product.get(
                            "article_name"
                        )
                        or ""
                    ),

                    str(
                        product.get(
                            "color"
                        )
                        or ""
                    ),

                    str(
                        product.get(
                            "thickness"
                        )
                        or ""
                    ),

                    str(
                        product.get(
                            "tannage"
                        )
                        or ""
                    ),

                    str(
                        product.get(
                            "animal"
                        )
                        or ""
                    ),

                    str(
                        product.get(
                            "origin"
                        )
                        or ""
                    ),
                ]
            ).casefold()

            if (
                search_lower
                and search_lower not in searchable_text
            ):
                continue

            filtered_products.append(
                product
            )

        st.caption(
            f"Showing {len(filtered_products)} "
            f"of {len(products)} articles"
        )

        st.divider()

        # ----------------------------------------------------
        # PRODUCTS
        # ----------------------------------------------------

        for product in filtered_products:

            leather_id = str(
                product.get(
                    "leather_id"
                )
                or "-"
            )

            article_name = str(
                product.get(
                    "article_name"
                )
                or "-"
            )

            is_active = bool(
                product.get(
                    "is_active"
                )
            )

            status_text = (
                "🟢 Active"
                if is_active
                else "🔴 Inactive"
            )

            with st.expander(
                f"{leather_id}  |  "
                f"{article_name}  |  "
                f"{status_text}",
                expanded=False,
            ):

                # ============================================
                # CURRENT INFORMATION
                # ============================================

                current_col1, current_col2 = st.columns(
                    [2, 3],
                    gap="large",
                )

                with current_col1:

                    main_url = get_image_url(
                        product.get(
                            "main_photo"
                        )
                    )

                    closeup_url = get_image_url(
                        product.get(
                            "closeup_photo"
                        )
                    )

                    if main_url:

                        st.image(
                            main_url,
                            caption="Main Photo",
                            width="stretch",
                        )

                    if closeup_url:

                        st.image(
                            closeup_url,
                            caption="Close-up Photo",
                            width="stretch",
                        )

                with current_col2:

                    st.markdown(
                        f"**Leather ID:** "
                        f"{leather_id}"
                    )

                    st.markdown(
                        f"**Article Name:** "
                        f"{article_name}"
                    )

                    st.markdown(
                        f"**Colour:** "
                        f"{product.get('color') or '-'}"
                    )

                    st.markdown(
                        f"**Thickness:** "
                        f"{product.get('thickness') or '-'}"
                    )

                    st.markdown(
                        f"**Animal:** "
                        f"{product.get('animal') or '-'}"
                    )

                    st.markdown(
                        f"**Tannage:** "
                        f"{product.get('tannage') or '-'}"
                    )

                    st.markdown(
                        f"**Origin:** "
                        f"{product.get('origin') or '-'}"
                    )

                st.divider()

                # ============================================
                # EDIT
                # ============================================

                st.markdown(
                    "### ✏️ Edit Article"
                )

                edit_col1, edit_col2 = st.columns(
                    2,
                    gap="large",
                )

                with edit_col1:

                    new_article_name = st.text_input(
                        "Article Name",
                        value=(
                            product.get(
                                "article_name"
                            )
                            or ""
                        ),
                        key=f"edit_name_{leather_id}",
                    )

                    new_color = st.text_input(
                        "Colour",
                        value=(
                            product.get(
                                "color"
                            )
                            or ""
                        ),
                        key=f"edit_color_{leather_id}",
                    )

                    new_thickness = st.text_input(
                        "Thickness",
                        value=(
                            product.get(
                                "thickness"
                            )
                            or ""
                        ),
                        key=f"edit_thickness_{leather_id}",
                    )

                    new_animal = st.text_input(
                        "Animal",
                        value=(
                            product.get(
                                "animal"
                            )
                            or ""
                        ),
                        key=f"edit_animal_{leather_id}",
                    )

                with edit_col2:

                    new_tannage = st.text_input(
                        "Tannage",
                        value=(
                            product.get(
                                "tannage"
                            )
                            or ""
                        ),
                        key=f"edit_tannage_{leather_id}",
                    )

                    new_origin = st.text_input(
                        "Origin",
                        value=(
                            product.get(
                                "origin"
                            )
                            or ""
                        ),
                        key=f"edit_origin_{leather_id}",
                    )

                    new_active = st.checkbox(
                        "Show in customer catalogue",
                        value=is_active,
                        key=f"edit_active_{leather_id}",
                    )

                if st.button(
                    "💾 Save Changes",
                    type="primary",
                    key=f"save_{leather_id}",
                ):

                    new_article_name = (
                        new_article_name
                        .strip()
                    )

                    if not new_article_name:

                        st.error(
                            "Article Name is required."
                        )

                    else:

                        valid, message = (
                            check_duplicate_product(
                                leather_id=leather_id,
                                article_name=new_article_name,
                                exclude_leather_id=leather_id,
                            )
                        )

                        if not valid:

                            st.error(message)

                        else:

                            try:

                                update_product(
                                    leather_id=leather_id,
                                    article_name=new_article_name,
                                    color=new_color.strip(),
                                    thickness=new_thickness.strip(),
                                    tannage=new_tannage.strip(),
                                    animal=new_animal.strip(),
                                    origin=new_origin.strip(),
                                    main_photo=product.get(
                                        "main_photo"
                                    ),
                                    closeup_photo=product.get(
                                        "closeup_photo"
                                    ),
                                    is_active=new_active,
                                )

                                st.cache_data.clear()

                                st.success(
                                    "Article updated successfully."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    "Unable to update article."
                                )

                                st.exception(e)

                st.divider()

                # ============================================
                # REPLACE PHOTOS
                # ============================================

                st.markdown(
                    "### 📷 Replace Photos"
                )

                photo_col1, photo_col2 = st.columns(
                    2,
                    gap="large",
                )

                with photo_col1:

                    new_main_photo = st.file_uploader(
                        "Replace Main Photo",
                        type=IMAGE_TYPES,
                        key=f"new_main_{leather_id}",
                    )

                with photo_col2:

                    new_closeup_photo = st.file_uploader(
                        "Replace Close-up Photo",
                        type=IMAGE_TYPES,
                        key=f"new_closeup_{leather_id}",
                    )

                if st.button(
                    "📷 Update Photos",
                    key=f"update_photos_{leather_id}",
                ):

                    if (
                        not new_main_photo
                        and not new_closeup_photo
                    ):

                        st.warning(
                            "Please select at least one photo."
                        )

                    else:

                        old_main = product.get(
                            "main_photo"
                        )

                        old_closeup = product.get(
                            "closeup_photo"
                        )

                        uploaded_main = None
                        uploaded_closeup = None

                        try:

                            # --------------------------------
                            # MAIN
                            # --------------------------------

                            if new_main_photo:

                                uploaded_main = upload_image(
                                    new_main_photo,
                                    leather_id,
                                    "main",
                                )

                                if not uploaded_main:

                                    st.stop()

                            else:

                                uploaded_main = old_main

                            # --------------------------------
                            # CLOSEUP
                            # --------------------------------

                            if new_closeup_photo:

                                uploaded_closeup = upload_image(
                                    new_closeup_photo,
                                    leather_id,
                                    "closeup",
                                )

                                if not uploaded_closeup:

                                    if (
                                        new_main_photo
                                        and uploaded_main
                                        and uploaded_main != old_main
                                    ):
                                        delete_storage_file(
                                            uploaded_main
                                        )

                                    st.stop()

                            else:

                                uploaded_closeup = old_closeup

                            # --------------------------------
                            # DATABASE
                            # --------------------------------

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    product.get(
                                        "article_name"
                                    )
                                    or ""
                                ),
                                color=(
                                    product.get(
                                        "color"
                                    )
                                    or ""
                                ),
                                thickness=(
                                    product.get(
                                        "thickness"
                                    )
                                    or ""
                                ),
                                tannage=(
                                    product.get(
                                        "tannage"
                                    )
                                    or ""
                                ),
                                animal=(
                                    product.get(
                                        "animal"
                                    )
                                    or ""
                                ),
                                origin=(
                                    product.get(
                                        "origin"
                                    )
                                    or ""
                                ),
                                main_photo=uploaded_main,
                                closeup_photo=uploaded_closeup,
                                is_active=is_active,
                            )

                            # --------------------------------
                            # DELETE OLD FILES
                            # --------------------------------

                            if (
                                new_main_photo
                                and old_main
                                and uploaded_main != old_main
                            ):

                                delete_storage_file(
                                    old_main
                                )

                            if (
                                new_closeup_photo
                                and old_closeup
                                and uploaded_closeup != old_closeup
                            ):

                                delete_storage_file(
                                    old_closeup
                                )

                            st.cache_data.clear()

                            st.success(
                                "Photos updated successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            # Clean newly uploaded files
                            # if DB update fails

                            if (
                                uploaded_main
                                and uploaded_main != old_main
                            ):

                                delete_storage_file(
                                    uploaded_main
                                )

                            if (
                                uploaded_closeup
                                and uploaded_closeup != old_closeup
                            ):

                                delete_storage_file(
                                    uploaded_closeup
                                )

                            st.error(
                                "Unable to update photos."
                            )

                            st.exception(e)

                st.divider()

                # ============================================
                # ACTIVATE / DEACTIVATE
                # ============================================

                st.markdown(
                    "### 🔄 Catalogue Status"
                )

                if is_active:

                    st.success(
                        "This article is currently visible "
                        "in the customer catalogue."
                    )

                    if st.button(
                        "🔴 Deactivate Article",
                        key=f"deactivate_{leather_id}",
                    ):

                        try:

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    product.get(
                                        "article_name"
                                    )
                                    or ""
                                ),
                                color=(
                                    product.get(
                                        "color"
                                    )
                                    or ""
                                ),
                                thickness=(
                                    product.get(
                                        "thickness"
                                    )
                                    or ""
                                ),
                                tannage=(
                                    product.get(
                                        "tannage"
                                    )
                                    or ""
                                ),
                                animal=(
                                    product.get(
                                        "animal"
                                    )
                                    or ""
                                ),
                                origin=(
                                    product.get(
                                        "origin"
                                    )
                                    or ""
                                ),
                                main_photo=product.get(
                                    "main_photo"
                                ),
                                closeup_photo=product.get(
                                    "closeup_photo"
                                ),
                                is_active=False,
                            )

                            st.cache_data.clear()

                            st.success(
                                "Article deactivated."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Unable to deactivate article."
                            )

                            st.exception(e)

                else:

                    st.warning(
                        "This article is currently hidden "
                        "from the customer catalogue."
                    )

                    if st.button(
                        "🟢 Activate Article",
                        key=f"activate_{leather_id}",
                    ):

                        try:

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    product.get(
                                        "article_name"
                                    )
                                    or ""
                                ),
                                color=(
                                    product.get(
                                        "color"
                                    )
                                    or ""
                                ),
                                thickness=(
                                    product.get(
                                        "thickness"
                                    )
                                    or ""
                                ),
                                tannage=(
                                    product.get(
                                        "tannage"
                                    )
                                    or ""
                                ),
                                animal=(
                                    product.get(
                                        "animal"
                                    )
                                    or ""
                                ),
                                origin=(
                                    product.get(
                                        "origin"
                                    )
                                    or ""
                                ),
                                main_photo=product.get(
                                    "main_photo"
                                ),
                                closeup_photo=product.get(
                                    "closeup_photo"
                                ),
                                is_active=True,
                            )

                            st.cache_data.clear()

                            st.success(
                                "Article activated."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Unable to activate article."
                            )

                            st.exception(e)

                st.divider()

                # ============================================
                # DELETE
                # ============================================

                st.markdown(
                    "### 🗑️ Delete Article"
                )

                st.warning(
                    "Deletion is permanent. "
                    "The database record and associated "
                    "photos will be removed."
                )

                confirm_delete = st.checkbox(
                    "I understand that this article will be permanently deleted.",
                    key=f"confirm_delete_{leather_id}",
                )

                if st.button(
                    "🗑️ Permanently Delete",
                    type="secondary",
                    key=f"delete_{leather_id}",
                    disabled=not confirm_delete,
                ):

                    with st.spinner(
                        "Deleting article..."
                    ):

                        if delete_product(product):

                            st.cache_data.clear()

                            st.success(
                                f"{leather_id} deleted successfully."
                            )

                            st.rerun()


# ============================================================
# CUSTOMER CATALOGUE
# ============================================================

def render_catalogue():

    # ========================================================
    # HEADER
    # ========================================================

    header_col, admin_col = st.columns(
        [8, 1],
        vertical_alignment="center",
    )

    with header_col:

        st.title("Leather Catalogue")

        st.caption(
            "Explore our leather collection"
        )

    with admin_col:

        if st.button(
            "⚙️ Admin",
            width="stretch",
            key="open_admin",
        ):

            st.session_state.show_admin_login = True

    st.divider()

    # ========================================================
    # PRODUCTS
    # ========================================================

    try:

        products = load_products()

    except Exception as e:

        st.error(
            "Unable to load leather catalogue."
        )

        st.exception(e)

        return

    if not products:

        st.info(
            "No leather articles are currently available."
        )

        return

    # ========================================================
    # FILTER VALUES
    # ========================================================

    animal_values = sorted(
        {
            str(
                p.get("animal")
            ).strip()
            for p in products
            if p.get("animal")
        }
    )

    tannage_values = sorted(
        {
            str(
                p.get("tannage")
            ).strip()
            for p in products
            if p.get("tannage")
        }
    )

    color_values = sorted(
        {
            str(
                p.get("color")
            ).strip()
            for p in products
            if p.get("color")
        }
    )

    origin_values = sorted(
        {
            str(
                p.get("origin")
            ).strip()
            for p in products
            if p.get("origin")
        }
    )

    # ========================================================
    # SEARCH
    # ========================================================

    search_text = st.text_input(
        "🔎 Search",
        placeholder=(
            "Search Leather ID, article, colour, "
            "thickness, tannage, animal or origin..."
        ),
        key="catalogue_search",
    )

    # ========================================================
    # FILTERS
    # ========================================================

    filter_col1, filter_col2, filter_col3, filter_col4 = (
        st.columns(4)
    )

    with filter_col1:

        selected_animal = st.selectbox(
            "Animal",
            ["All"] + animal_values,
            key="filter_animal",
        )

    with filter_col2:

        selected_tannage = st.selectbox(
            "Tannage",
            ["All"] + tannage_values,
            key="filter_tannage",
        )

    with filter_col3:

        selected_color = st.selectbox(
            "Colour",
            ["All"] + color_values,
            key="filter_color",
        )

    with filter_col4:

        selected_origin = st.selectbox(
            "Origin",
            ["All"] + origin_values,
            key="filter_origin",
        )

    sort_option = st.selectbox(
        "Sort by",
        [
            "Leather ID",
            "Article",
            "Animal",
            "Colour",
        ],
        key="catalogue_sort",
    )

    # ========================================================
    # FILTER PRODUCTS
    # ========================================================

    search_lower = (
        search_text
        .strip()
        .casefold()
    )

    filtered_products = []

    for product in products:

        # Search
        searchable_text = " ".join(
            [
                str(
                    product.get(
                        "leather_id"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "article_name"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "color"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "thickness"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "tannage"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "animal"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "origin"
                    )
                    or ""
                ),
            ]
        ).casefold()

        if (
            search_lower
            and search_lower not in searchable_text
        ):

            continue

        # Animal
        if (
            selected_animal != "All"
            and str(
                product.get("animal")
                or ""
            ).strip()
            != selected_animal
        ):

            continue

        # Tannage
        if (
            selected_tannage != "All"
            and str(
                product.get("tannage")
                or ""
            ).strip()
            != selected_tannage
        ):

            continue

        # Colour
        if (
            selected_color != "All"
            and str(
                product.get("color")
                or ""
            ).strip()
            != selected_color
        ):

            continue

        # Origin
        if (
            selected_origin != "All"
            and str(
                product.get("origin")
                or ""
            ).strip()
            != selected_origin
        ):

            continue

        filtered_products.append(
            product
        )

    # ========================================================
    # SORT
    # ========================================================

    if sort_option == "Leather ID":

        filtered_products.sort(
            key=lambda x: str(
                x.get("leather_id")
                or ""
            ).casefold()
        )

    elif sort_option == "Article":

        filtered_products.sort(
            key=lambda x: str(
                x.get("article_name")
                or ""
            ).casefold()
        )

    elif sort_option == "Animal":

        filtered_products.sort(
            key=lambda x: str(
                x.get("animal")
                or ""
            ).casefold()
        )

    elif sort_option == "Colour":

        filtered_products.sort(
            key=lambda x: str(
                x.get("color")
                or ""
            ).casefold()
        )

    st.caption(
        f"{len(filtered_products)} "
        f"article(s) found"
    )

    st.divider()

    # ========================================================
    # PRODUCT GRID
    # ========================================================

    if not filtered_products:

        st.info(
            "No leather articles match your search."
        )

        return

    cards_per_row = 3

    for row_start in range(
        0,
        len(filtered_products),
        cards_per_row,
    ):

        row_products = filtered_products[
            row_start:
            row_start + cards_per_row
        ]

        columns = st.columns(
            cards_per_row,
            gap="large",
        )

        for column, product in zip(
            columns,
            row_products,
        ):

            with column:

                leather_id = str(
                    product.get(
                        "leather_id"
                    )
                    or "-"
                )

                article_name = str(
                    product.get(
                        "article_name"
                    )
                    or "-"
                )

                main_url = get_image_url(
                    product.get(
                        "main_photo"
                    )
                )

                closeup_url = get_image_url(
                    product.get(
                        "closeup_photo"
                    )
                )

                # --------------------------------------------
                # IMAGE
                # --------------------------------------------

                if main_url or closeup_url:

                    render_image_slider(
                        main_url,
                        closeup_url,
                        height=320,
                    )

                else:

                    st.markdown(
                        """
                        <div style="
                            height:320px;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            border-radius:12px;
                            background:#f5f5f5;
                            color:#888;
                        ">
                            No Image
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # --------------------------------------------
                # INFORMATION
                # --------------------------------------------

                st.markdown(
                    f"### {html.escape(article_name)}"
                )

                st.caption(
                    f"Leather ID: {html.escape(leather_id)}"
                )

                info_html = f"""
                <div style="
                    font-size:14px;
                    line-height:1.7;
                ">

                    <b>Colour:</b>
                    {html.escape(
                        str(
                            product.get("color")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Thickness:</b>
                    {html.escape(
                        str(
                            product.get("thickness")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Animal:</b>
                    {html.escape(
                        str(
                            product.get("animal")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Tannage:</b>
                    {html.escape(
                        str(
                            product.get("tannage")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Origin:</b>
                    {html.escape(
                        str(
                            product.get("origin")
                            or "-"
                        )
                    )}

                </div>
                """

                st.markdown(
                    info_html,
                    unsafe_allow_html=True,
                )

                st.write("")

                if st.button(
                    "View Details",
                    width="stretch",
                    key=f"view_{leather_id}",
                ):

                    show_product_details(
                        product
                    )

                st.write("")


# ============================================================
# APP ROUTING
# ============================================================

if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False


# ============================================================
# ADMIN MODE
# ============================================================

if st.session_state.show_admin_login:

    # Back to catalogue
    if st.button(
        "← Back to Catalogue",
        key="back_to_catalogue",
    ):

        st.session_state.show_admin_login = False
        st.session_state.admin_authenticated = False

        st.rerun()

    st.divider()

    if check_admin_password():

        render_admin_panel()

# ============================================================
# CUSTOMER MODE
# ============================================================

else:

    render_catalogue()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Bhartiya Fashions • Leather Catalogue"
)
2. .streamlit/secrets.toml

Create:

SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"

# Customer/public key
SUPABASE_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"

# NEVER expose this in frontend/client code
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"

# Strong private admin password
ADMIN_PASSWORD = "YOUR_STRONG_ADMIN_PASSWORD"

Your existing admin code follows this same separation: customer/public connection versus service-role admin connection.

3. Important: database uniqueness

Your Python code checks duplicate Leather ID and Article Name case-insensitively, as your previous admin code did.

But do not rely only on Python validation. Two simultaneous requests could still create duplicates.

Run this in Supabase SQL Editor:

-- Leather ID must be unique
CREATE UNIQUE INDEX IF NOT EXISTS
leather_products_leather_id_unique
ON public.leather_products (LOWER(TRIM(leather_id)));

-- Article Name must be unique
CREATE UNIQUE INDEX IF NOT EXISTS
leather_products_article_name_unique
ON public.leather_products (LOWER(TRIM(article_name)));

This gives you database-level protection as well.

4. Your project structure
leather-catalogue/
│
├── app.py
│
├── requirements.txt
│
└── .streamlit/
    └── secrets.toml

requirements.txt:

streamlit
supabase
Pillow
5. Security point

The customer does not receive the service-role key. It stays inside Streamlit secrets and is only used by the server-side admin functions.

Your uploaded admin implementation also uses the service-role key for database/storage administration, including image upload/delete and CRUD operations.

The admin area is reached through:

Catalogue → ⚙️ Admin → Password → Admin panel

The admin panel provides:

➕ Add Leather
📋 Manage Catalogue

    ✏️ Edit
    📷 Replace Photos
    🟢 Activate
    🔴 Deactivate
    🗑️ Delete
    ↻ Refresh
    Logout

One important distinction: this protects the admin operations with a password; it does not make the customer catalogue itself private. If by “all are confidential” you mean that even the catalogue/products/images must only be visible after login, then the architecture should instead have a login before the catalogue itself, and the Supabase storage bucket should not be public.

import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
from PIL import Image
import uuid

=========================================================
PAGE CONFIG
=========================================================

st.set_page_config(
page_title="Catalogue Admin",
page_icon="⚙️",
layout="wide",
)

=========================================================
CONSTANTS
=========================================================

TABLE_NAME = "leather_products"
BUCKET_NAME = "leather-images"

=========================================================
SUPABASE CONNECTION
=========================================================

@st.cache_resource
def get_admin_supabase():

return create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
)

try:

supabase = get_admin_supabase()

except Exception as e:

st.error(
    "Supabase admin connection could not be established."
)

st.info(
    "Please add SUPABASE_SERVICE_ROLE_KEY "
    "to Streamlit secrets."
)

st.exception(e)

st.stop()
=========================================================
ADMIN LOGIN
=========================================================

def check_admin_password():

if st.session_state.get(
    "admin_authenticated",
    False,
):
    return True

st.title("🔐 Catalogue Administration")

st.caption(
    "Restricted area for managing the leather catalogue."
)

password = st.text_input(
    "Admin Password",
    type="password",
    placeholder="Enter admin password",
)

if st.button(
    "Login",
    type="primary",
    width="stretch",
):

    admin_password = st.secrets.get(
        "ADMIN_PASSWORD"
    )

    if not admin_password:

        st.error(
            "ADMIN_PASSWORD is not configured "
            "in Streamlit secrets."
        )

        return False

    if password == admin_password:

        st.session_state[
            "admin_authenticated"
        ] = True

        st.rerun()

    else:

        st.error(
            "Incorrect password."
        )

return False

if not check_admin_password():

st.stop()
=========================================================
HEADER
=========================================================

header_col, logout_col = st.columns(
[8, 1],
vertical_alignment="center",
)

with header_col:

st.title("⚙️ Catalogue Administration")

st.caption(
    "Add, edit, activate, deactivate and delete "
    "leather catalogue articles."
)

with logout_col:

if st.button(
    "Logout",
    width="stretch",
):

    st.session_state[
        "admin_authenticated"
    ] = False

    st.rerun()

st.divider()

=========================================================
IMAGE URL
=========================================================

def get_image_url(filename):

if not filename:

    return None

filename = str(
    filename
).strip()

if not filename:

    return None

return (
    f"{st.secrets['SUPABASE_URL']}"
    f"/storage/v1/object/public/"
    f"{BUCKET_NAME}/"
    f"{quote(filename)}"
)
=========================================================
LOAD IMAGE
=========================================================

@st.cache_data(
ttl=600,
show_spinner=False,
)
def load_image(image_url):

if not image_url:

    return None

try:

    with urlopen(
        image_url,
        timeout=20,
    ) as response:

        image_bytes = response.read()

    return Image.open(
        BytesIO(image_bytes)
    ).convert("RGB")

except Exception:

    return None
=========================================================
LOAD PRODUCTS
=========================================================

@st.cache_data(
ttl=60,
show_spinner=False,
)
def load_all_products():

response = (
    supabase
    .table(TABLE_NAME)
    .select(
        """
        leather_id,
        article_name,
        color,
        thickness,
        tannage,
        animal,
        origin,
        main_photo,
        closeup_photo,
        is_active
        """
    )
    .order(
        "leather_id"
    )
    .execute()
)

return response.data or []
=========================================================
DUPLICATE VALIDATION
=========================================================

def check_duplicate_product(leather_id, article_name, exclude_leather_id=None):
"""Case-insensitive duplicate check for Leather ID and Article Name."""
lid = leather_id.strip().casefold()
name = article_name.strip().casefold()
for product in load_all_products():
existing_id = str(product.get("leather_id") or "").strip()
existing_name = str(product.get("article_name") or "").strip()
if exclude_leather_id and existing_id.casefold() == exclude_leather_id.strip().casefold():
continue
if existing_id.casefold() == lid:
return False, f"Leather ID '{leather_id}' already exists."
if existing_name.casefold() == name:
return False, f"Article Name '{article_name}' already exists."
return True, ""

=========================================================
STORAGE HELPERS
=========================================================

def upload_image(
uploaded_file,
leather_id,
photo_type,
):

if uploaded_file is None:

    return None

original_name = (
    uploaded_file.name
    or "image.jpg"
)

extension = (
    original_name
    .rsplit(".", 1)[-1]
    .lower()
)

if extension not in [
    "jpg",
    "jpeg",
    "png",
    "webp",
]:

    extension = "jpg"

unique_id = (
    uuid.uuid4()
    .hex[:8]
)

filename = (
    f"{leather_id}_"
    f"{photo_type}_"
    f"{unique_id}."
    f"{extension}"
)

file_bytes = uploaded_file.getvalue()

content_type = (
    uploaded_file.type
    or "image/jpeg"
)

try:

    supabase.storage.from_(
        BUCKET_NAME
    ).upload(
        filename,
        file_bytes,
        {
            "content-type": content_type,
            "upsert": False,
        },
    )

    return filename

except Exception as e:

    st.error(
        f"Unable to upload {photo_type} photo."
    )

    st.exception(e)

    return None

def delete_storage_file(filename):

if not filename:

    return

try:

    supabase.storage.from_(
        BUCKET_NAME
    ).remove(
        [filename]
    )

except Exception as e:

    st.warning(
        f"Could not delete storage file: "
        f"{filename}"
    )

    st.caption(
        str(e)
    )
=========================================================
UPDATE DATABASE
=========================================================

def update_product(
leather_id,
article_name,
color,
thickness,
tannage,
animal,
origin,
main_photo,
closeup_photo,
is_active,
):

response = (
    supabase
    .table(TABLE_NAME)
    .update(
        {
            "article_name": article_name,
            "color": color,
            "thickness": thickness,
            "tannage": tannage,
            "animal": animal,
            "origin": origin,
            "main_photo": main_photo,
            "closeup_photo": closeup_photo,
            "is_active": is_active,
        }
    )
    .eq(
        "leather_id",
        leather_id,
    )
    .execute()
)

return response
=========================================================
CREATE PRODUCT
=========================================================

def create_product(
leather_id,
article_name,
color,
thickness,
tannage,
animal,
origin,
main_photo,
closeup_photo,
is_active,
):

response = (
    supabase
    .table(TABLE_NAME)
    .insert(
        {
            "leather_id": leather_id,
            "article_name": article_name,
            "color": color,
            "thickness": thickness,
            "tannage": tannage,
            "animal": animal,
            "origin": origin,
            "main_photo": main_photo,
            "closeup_photo": closeup_photo,
            "is_active": is_active,
        }
    )
    .execute()
)

return response
=========================================================
DELETE PRODUCT
=========================================================

def delete_product(product):

leather_id = product.get(
    "leather_id"
)

main_photo = product.get(
    "main_photo"
)

closeup_photo = product.get(
    "closeup_photo"
)

try:

    (
        supabase
        .table(TABLE_NAME)
        .delete()
        .eq(
            "leather_id",
            leather_id,
        )
        .execute()
    )

    if main_photo:

        delete_storage_file(
            main_photo
        )

    if (
        closeup_photo
        and closeup_photo != main_photo
    ):

        delete_storage_file(
            closeup_photo
        )

    return True

except Exception as e:

    st.error(
        "Unable to delete leather article."
    )

    st.exception(e)

    return False
=========================================================
REFRESH
=========================================================

refresh_col, status_col = st.columns(
[1, 5],
vertical_alignment="center",
)

with refresh_col:

if st.button(
    "↻ Refresh",
    width="stretch",
):

    st.cache_data.clear()

    st.rerun()

with status_col:

try:

    products = load_all_products()

    st.success(
        f"{len(products)} leather articles found."
    )

except Exception as e:

    st.error(
        "Unable to load products."
    )

    st.exception(e)

    st.stop()

st.divider()

=========================================================
TABS
=========================================================

tab_add, tab_manage = st.tabs(
[
"➕ Add Leather",
"📋 Manage Catalogue",
]
)

=========================================================
ADD LEATHER
=========================================================

with tab_add:

st.subheader(
    "Add New Leather Article"
)

st.caption(
    "Create a new product and optionally upload "
    "main and close-up photos."
)

with st.form(
    "add_product_form",
    clear_on_submit=False,
):

    col1, col2 = st.columns(
        2,
        gap="large",
    )

    with col1:

        leather_id = st.text_input(
            "Leather ID *",
            placeholder="Example: BIL00021",
        )

        article_name = st.text_input(
            "Article Name *",
            placeholder="Example: Cow Lionel",
        )

        color = st.text_input(
            "Colour",
            placeholder="Example: Golden Spice",
        )

        thickness = st.text_input(
            "Thickness",
            placeholder="Example: 0.7 - 0.8",
        )

    with col2:

        animal = st.text_input(
            "Animal",
            placeholder="Example: Cow",
        )

        tannage = st.text_input(
            "Tannage",
            placeholder="Example: Semi Veg",
        )

        origin = st.text_input(
            "Origin",
            placeholder="Example: Turkey",
        )

        is_active = st.checkbox(
            "Show in customer catalogue",
            value=True,
        )

    st.divider()

    photo_col1, photo_col2 = st.columns(
        2,
        gap="large",
    )

    with photo_col1:

        main_photo_file = st.file_uploader(
            "Main Photo",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
            key="add_main_photo",
        )

        if main_photo_file:

            st.image(
                main_photo_file,
                caption="Main Photo Preview",
                width="stretch",
            )

    with photo_col2:

        closeup_photo_file = st.file_uploader(
            "Close-up Photo",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
            key="add_closeup_photo",
        )

        if closeup_photo_file:

            st.image(
                closeup_photo_file,
                caption="Close-up Photo Preview",
                width="stretch",
            )

    st.divider()

    submitted = st.form_submit_button(
        "➕ Add Leather Article",
        type="primary",
        width="stretch",
    )

if submitted:

    leather_id = leather_id.strip()
    article_name = article_name.strip()

    if not leather_id:

        st.error(
            "Leather ID is required."
        )

    elif not article_name:

        st.error(
            "Article Name is required."
        )

    else:

        is_valid, duplicate_message = check_duplicate_product(
            leather_id=leather_id,
            article_name=article_name,
        )

        if not is_valid:
            st.error(duplicate_message)
        else:

            with st.spinner(
                "Creating leather article..."
            ):

                main_photo_name = None
                closeup_photo_name = None

                # -----------------------------------------
                # MAIN PHOTO
                # -----------------------------------------

                if main_photo_file:

                    main_photo_name = (
                        upload_image(
                            main_photo_file,
                            leather_id,
                            "main",
                        )
                    )

                    if (
                        main_photo_name
                        is None
                    ):

                        st.stop()

                # -----------------------------------------
                # CLOSE-UP PHOTO
                # -----------------------------------------

                if closeup_photo_file:

                    closeup_photo_name = (
                        upload_image(
                            closeup_photo_file,
                            leather_id,
                            "closeup",
                        )
                    )

                    if (
                        closeup_photo_name
                        is None
                    ):

                        if main_photo_name:

                            delete_storage_file(
                                main_photo_name
                            )

                        st.stop()

                # -----------------------------------------
                # DATABASE
                # -----------------------------------------

                try:

                    create_product(
                        leather_id=leather_id,
                        article_name=article_name,
                        color=color.strip(),
                        thickness=thickness.strip(),
                        tannage=tannage.strip(),
                        animal=animal.strip(),
                        origin=origin.strip(),
                        main_photo=main_photo_name,
                        closeup_photo=closeup_photo_name,
                        is_active=is_active,
                    )

                    st.cache_data.clear()

                    st.success(
                        f"{leather_id} "
                        "was added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    # If DB insert fails,
                    # remove uploaded images.

                    if main_photo_name:

                        delete_storage_file(
                            main_photo_name
                        )

                    if closeup_photo_name:

                        delete_storage_file(
                            closeup_photo_name
                        )

                    st.error(
                        "Unable to create "
                        "the leather article."
                    )

                    st.exception(e)
=========================================================
MANAGE CATALOGUE
=========================================================

with tab_manage:

st.subheader(
    "Manage Existing Articles"
)

st.caption(
    "Search, edit, activate/deactivate "
    "or delete leather articles."
)

# -----------------------------------------------------
# SEARCH
# -----------------------------------------------------

search_text = st.text_input(
    "Search catalogue",
    placeholder=(
        "Search Leather ID, article, colour, "
        "animal, tannage or origin..."
    ),
    key="admin_search",
)

search_lower = (
    search_text
    .strip()
    .lower()
)

filtered_products = []

for product in products:

    searchable_text = " ".join(
        [
            str(
                product.get(
                    "leather_id"
                )
                or ""
            ),

            str(
                product.get(
                    "article_name"
                )
                or ""
            ),

            str(
                product.get(
                    "color"
                )
                or ""
            ),

            str(
                product.get(
                    "thickness"
                )
                or ""
            ),

            str(
                product.get(
                    "tannage"
                )
                or ""
            ),

            str(
                product.get(
                    "animal"
                )
                or ""
            ),

            str(
                product.get(
                    "origin"
                )
                or ""
            ),
        ]
    ).lower()

    if (
        search_lower
        and search_lower
        not in searchable_text
    ):

        continue

    filtered_products.append(
        product
    )

st.caption(
    f"Showing {len(filtered_products)} "
    f"of {len(products)} articles"
)

st.divider()


# =====================================================
# PRODUCT LIST
# =====================================================

for product in filtered_products:

    leather_id = str(
        product.get(
            "leather_id"
        )
        or "-"
    )

    article_name = str(
        product.get(
            "article_name"
        )
        or "-"
    )

    main_photo = product.get(
        "main_photo"
    )

    closeup_photo = product.get(
        "closeup_photo"
    )

    is_active = bool(
        product.get(
            "is_active"
        )
    )

    # -------------------------------------------------
    # PRODUCT EXPANDER
    # -------------------------------------------------

    with st.expander(
        f"{leather_id}  |  {article_name}",
        expanded=False,
    ):

        # =============================================
        # TOP INFORMATION
        # =============================================

        info_col, status_col = st.columns(
            [5, 1],
            vertical_alignment="center",
        )

        with info_col:

            st.markdown(
                f"### {article_name}"
            )

            st.caption(
                f"Leather ID: {leather_id}"
            )

        with status_col:

            if is_active:

                st.success(
                    "ACTIVE"
                )

            else:

                st.warning(
                    "INACTIVE"
                )


        st.divider()


        # =============================================
        # CURRENT PHOTOS
        # =============================================

        photo_col1, photo_col2 = st.columns(
            2,
            gap="large",
        )

        with photo_col1:

            st.markdown(
                "**Main Photo**"
            )

            if main_photo:

                main_url = get_image_url(
                    main_photo
                )

                main_image = load_image(
                    main_url
                )

                if main_image:

                    st.image(
                        main_image,
                        width="stretch",
                    )

                else:

                    st.warning(
                        "Main photo could not "
                        "be loaded."
                    )

                st.caption(
                    main_photo
                )

            else:

                st.info(
                    "No main photo."
                )

        with photo_col2:

            st.markdown(
                "**Close-up Photo**"
            )

            if closeup_photo:

                closeup_url = get_image_url(
                    closeup_photo
                )

                closeup_image = load_image(
                    closeup_url
                )

                if closeup_image:

                    st.image(
                        closeup_image,
                        width="stretch",
                    )

                else:

                    st.warning(
                        "Close-up photo could "
                        "not be loaded."
                    )

                st.caption(
                    closeup_photo
                )

            else:

                st.info(
                    "No close-up photo."
                )


        st.divider()


        # =============================================
        # EDIT FORM
        # =============================================

        st.markdown(
            "### Edit Article"
        )

        edit_col1, edit_col2 = st.columns(
            2,
            gap="large",
        )

        with edit_col1:

            edit_article_name = st.text_input(
                "Article Name",
                value=str(
                    product.get(
                        "article_name"
                    )
                    or ""
                ),
                key=f"name_{leather_id}",
            )

            edit_color = st.text_input(
                "Colour",
                value=str(
                    product.get(
                        "color"
                    )
                    or ""
                ),
                key=f"color_{leather_id}",
            )

            edit_thickness = st.text_input(
                "Thickness",
                value=str(
                    product.get(
                        "thickness"
                    )
                    or ""
                ),
                key=f"thickness_{leather_id}",
            )

            edit_animal = st.text_input(
                "Animal",
                value=str(
                    product.get(
                        "animal"
                    )
                    or ""
                ),
                key=f"animal_{leather_id}",
            )

        with edit_col2:

            edit_tannage = st.text_input(
                "Tannage",
                value=str(
                    product.get(
                        "tannage"
                    )
                    or ""
                ),
                key=f"tannage_{leather_id}",
            )

            edit_origin = st.text_input(
                "Origin",
                value=str(
                    product.get(
                        "origin"
                    )
                    or ""
                ),
                key=f"origin_{leather_id}",
            )

            edit_active = st.checkbox(
                "Show in customer catalogue",
                value=is_active,
                key=f"active_{leather_id}",
            )


        st.markdown(
            "### Replace Photos"
        )

        new_photo_col1, new_photo_col2 = (
            st.columns(
                2,
                gap="large",
            )
        )

        with new_photo_col1:

            new_main_photo = st.file_uploader(
                "Replace Main Photo",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ],
                key=f"new_main_{leather_id}",
            )

            if new_main_photo:

                st.image(
                    new_main_photo,
                    caption="New Main Photo",
                    width="stretch",
                )

        with new_photo_col2:

            new_closeup_photo = st.file_uploader(
                "Replace Close-up Photo",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ],
                key=f"new_closeup_{leather_id}",
            )

            if new_closeup_photo:

                st.image(
                    new_closeup_photo,
                    caption="New Close-up Photo",
                    width="stretch",
                )


        # =============================================
        # ACTION BUTTONS
        # =============================================

        st.divider()

        action_col1, action_col2, action_col3 = (
            st.columns(
                [2, 2, 2],
                gap="medium",
            )
        )


        # ---------------------------------------------
        # SAVE CHANGES
        # ---------------------------------------------

        with action_col1:

            save_clicked = st.button(
                "💾 Save Changes",
                key=f"save_{leather_id}",
                type="primary",
                width="stretch",
            )


        # ---------------------------------------------
        # ACTIVATE / DEACTIVATE
        # ---------------------------------------------

        with action_col2:

            if is_active:

                status_clicked = st.button(
                    "⏸ Deactivate",
                    key=f"status_{leather_id}",
                    width="stretch",
                )

            else:

                status_clicked = st.button(
                    "▶ Activate",
                    key=f"status_{leather_id}",
                    width="stretch",
                )


        # ---------------------------------------------
        # DELETE
        # ---------------------------------------------

        with action_col3:

            delete_clicked = st.button(
                "🗑️ Delete",
                key=f"delete_{leather_id}",
                width="stretch",
            )


        # =============================================
        # SAVE
        # =============================================

        if save_clicked:

            if not edit_article_name.strip():
                st.error("Article Name cannot be empty.")

            else:
                is_valid, duplicate_message = check_duplicate_product(
                    leather_id=leather_id,
                    article_name=edit_article_name,
                    exclude_leather_id=leather_id,
                )

                if not is_valid:
                    st.error(duplicate_message)
                else:
                    new_main_photo_name = main_photo

                    new_closeup_photo_name = (
                        closeup_photo
                    )

                    upload_success = True

                    # -------------------------------------
                    # NEW MAIN PHOTO
                    # -------------------------------------

                    if new_main_photo:

                        uploaded_main_name = (
                            upload_image(
                                new_main_photo,
                                leather_id,
                                "main",
                            )
                        )

                        if uploaded_main_name:

                            new_main_photo_name = (
                                uploaded_main_name
                            )

                        else:

                            upload_success = False


                    # -------------------------------------
                    # NEW CLOSE-UP PHOTO
                    # -------------------------------------

                    if (
                        upload_success
                        and new_closeup_photo
                    ):

                        uploaded_closeup_name = (
                            upload_image(
                                new_closeup_photo,
                                leather_id,
                                "closeup",
                            )
                        )

                        if uploaded_closeup_name:

                            new_closeup_photo_name = (
                                uploaded_closeup_name
                            )

                        else:

                            upload_success = False


                    if upload_success:

                        try:

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    edit_article_name
                                    .strip()
                                ),
                                color=(
                                    edit_color
                                    .strip()
                                ),
                                thickness=(
                                    edit_thickness
                                    .strip()
                                ),
                                tannage=(
                                    edit_tannage
                                    .strip()
                                ),
                                animal=(
                                    edit_animal
                                    .strip()
                                ),
                                origin=(
                                    edit_origin
                                    .strip()
                                ),
                                main_photo=(
                                    new_main_photo_name
                                ),
                                closeup_photo=(
                                    new_closeup_photo_name
                                ),
                                is_active=(
                                    edit_active
                                ),
                            )

                            # ---------------------------------
                            # DELETE OLD MAIN PHOTO
                            # ---------------------------------

                            if (
                                new_main_photo
                                and main_photo
                                and main_photo
                                != new_main_photo_name
                            ):

                                delete_storage_file(
                                    main_photo
                                )


                            # ---------------------------------
                            # DELETE OLD CLOSE-UP PHOTO
                            # ---------------------------------

                            if (
                                new_closeup_photo
                                and closeup_photo
                                and closeup_photo
                                != new_closeup_photo_name
                            ):

                                delete_storage_file(
                                    closeup_photo
                                )


                            st.cache_data.clear()

                            st.success(
                                f"{leather_id} "
                                "updated successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Unable to update "
                                "the article."
                            )

                            st.exception(e)


        # =============================================
        # ACTIVATE / DEACTIVATE
        # =============================================

        if status_clicked:

            try:

                (
                    supabase
                    .table(TABLE_NAME)
                    .update(
                        {
                            "is_active":
                                not is_active
                        }
                    )
                    .eq(
                        "leather_id",
                        leather_id,
                    )
                    .execute()
                )

                st.cache_data.clear()

                if is_active:

                    st.success(
                        f"{leather_id} "
                        "has been deactivated."
                    )

                else:

                    st.success(
                        f"{leather_id} "
                        "has been activated."
                    )

                st.rerun()

            except Exception as e:

                st.error(
                    "Unable to change "
                    "article status."
                )

                st.exception(e)

        
        # =============================================
        # DELETE
        # =============================================
        
        if delete_clicked:
        
            st.session_state["delete_confirm_id"] = leather_id
        
        
        # Show confirmation if this product is waiting
        # for deletion confirmation.
        
        if (
            st.session_state.get("delete_confirm_id")
            == leather_id
        ):
        
            st.warning(
                f"Are you sure you want to permanently delete "
                f"**{leather_id} | {article_name}**?"
            )
        
            confirm_col1, confirm_col2 = st.columns(
                2,
                gap="medium",
            )
        
            with confirm_col1:
        
                confirm_delete = st.button(
                    "🗑️ Yes, permanently delete",
                    key=f"confirm_delete_{leather_id}",
                    type="primary",
                    width="stretch",
                )
        
            with confirm_col2:
        
                cancel_delete = st.button(
                    "Cancel",
                    key=f"cancel_delete_{leather_id}",
                    width="stretch",
                )
        
            if cancel_delete:
        
                st.session_state.pop(
                    "delete_confirm_id",
                    None,
                )
        
                st.rerun()
        
            if confirm_delete:
        
                with st.spinner(
                    f"Deleting {leather_id}..."
                ):
        
                    try:
        
                        # -----------------------------------------
                        # DELETE DATABASE RECORD FIRST
                        # -----------------------------------------
        
                        delete_response = (
                            supabase
                            .table(TABLE_NAME)
                            .delete()
                            .eq(
                                "leather_id",
                                leather_id,
                            )
                            .execute()
                        )
        
                        # -----------------------------------------
                        # DELETE MAIN PHOTO
                        # -----------------------------------------
        
                        if main_photo:
        
                            delete_storage_file(
                                main_photo
                            )
        
                        # -----------------------------------------
                        # DELETE CLOSE-UP PHOTO
                        # -----------------------------------------
        
                        if (
                            closeup_photo
                            and closeup_photo != main_photo
                        ):
        
                            delete_storage_file(
                                closeup_photo
                            )
        
                        # -----------------------------------------
                        # CLEAR DELETE STATE
                        # -----------------------------------------
        
                        st.session_state.pop(
                            "delete_confirm_id",
                            None,
                        )
        
                        # -----------------------------------------
                        # CLEAR CACHE
                        # -----------------------------------------
        
                        st.cache_data.clear()
        
                        st.success(
                            f"{leather_id} was permanently deleted."
                        )
        
                        st.rerun()
        
                    except Exception as e:
        
                        st.error(
                            f"Unable to delete {leather_id}."
                        )
        
                        st.exception(e)
=========================================================
FOOTER
=========================================================

st.divider()

st.caption(
"Leather Catalogue Administration • "
"Bhartiya Fashions"
)

