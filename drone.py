from tkinter import *
from tkinter import messagebox, filedialog, Menu
from PIL import Image, ImageDraw, ImageGrab
import tkinter.messagebox as alert

old_x, old_y = 0, 0
pen_color = "black"
bg_color = "white"
created = []
new = []
created_element_info = []



def updateCoordinates(event):
    global old_x, old_y
    print("Called!!!!")
    old_x, old_y = event.x, event.y
    print(old_x,old_y)

def addLine(event):
    global old_x, old_y
    c.create_line((old_x, old_y, event.x, event.y), fill=pen_color)
    old_x, old_y = event.x, event.y

def clearCanvas():
    c.delete("all")

def exportAsImage():
    filename = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg'), ('GIF', '*.gif')], title="Save the image as...")
    main_frame.update()
    x = root.winfo_rootx() + main_frame.winfo_x()
    y = root.winfo_rooty() + main_frame.winfo_y()
    width = main_frame.winfo_width()
    height = main_frame.winfo_height()

    img = ImageGrab.grab(bbox=(x, y, x+width, y+height))
    img.save(filename)
    print("Image saved as '{filename}")
    messagebox.showinfo("Export as image", f"Image exported successfully to '{filename}'")


def createElms():
    global shape, old_x,old_y
    if shape == "Rectangle":
        a = c.create_rectangle(old_x, old_y, x, y,activewidth=2)
    elif shape == "Oval":
        print("Oval Called")
        print(shape)
        a = c.create_oval(old_x, old_y, x, y,activewidth=2)
    elif shape == "Polygan":
        a = c.create_polygon(
            old_x, old_y, x, y, old_x, old_y,activewidth=2)
    elif shape == "Arc":
        a = c.create_arc(old_x, old_y, x, y,activewidth=2)
    elif shape == "Line":
        a = c.create_line(old_x, old_y, x, y,
                               width=2,activewidth=2,
                               capstyle=ROUND, smooth=TRUE, splinesteps=3)
    else:
        c.create_line((old_x, old_y, x, y), fill=pen_color)
        old_x, old_y = x, y  
    return a

def createLine(e=""):
    global x, y, created, new , old_y,old_x
    # line_width
    # try:
    print(old_y,old_x)
    if e != "Get":
        x = e.x
        y = e.y
    status.set(f"Position : x - {x} , y - {y}")
    statusbar.update()
    a = createElms()
    if e != "Get":
        created.append(a)
        for item in created[:-1]:
            c.delete(item)
    # except Exception as e:
    #     alert.showerror("Some Error Occurred!", e)

def saveDrawing(e=""):
    global created, shape, color
    global created_element_info
    
    try:    
        new.append(created[-1])
    except IndexError:
        pass
    created = []
    created_element_info_new = {
        "type": shape,
        "prev_x": old_x,
        "prev_y": old_y,
        "x": x,
        "y": y
    }
    created_element_info.append(created_element_info_new)
    # print(created_element_info)


def shapechanger(e=""):
    global shape
    if shape is not radiovalue.get():
        shape = radiovalue.get()
    else:
        shape = ""
    print(shape)

def captureMotion(e=""):
    global x,y,old_x,old_y
    status.set(f"Position : x - {e.x} , y - {e.y}")
    # x = e.x
    # y = e.y
    # old_x = e.x
    # old_y = e.y
    statusbar.update()


# << Trying for only white canvas , maybe putting it in seperate frame than mainframewill work >>
# def exportAsImage():
#     filename = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg'), ('GIF', '*.gif')], title="Save the image as...")
#     if filename:
#         x, y, w, h = c.bbox("all")
#         img = Image.new("RGBA", (w, h), bg_color)
#         draw = ImageDraw.Draw(img)
#         draw.rectangle((0, 0, w, h), fill=bg_color)
#         draw.line([(x1 - x, y1 - y) for (x1, y1) in c.coords("all")], fill=pen_color, width=2)
#         img.save(filename)
#         messagebox.showinfo("Export as Image", f"Image saved as '{filename}'")

#Root Create + Setup
root = Tk()
root.title("Drawing Pad")
root.minsize(600, 400)
root.update() 

width = root.winfo_width()  
height = root.winfo_height()  

# root.columnconfigure(0, weight=int(0.9*width))
# root.rowconfigure(0, weight=int(0.9*height))

main_frame = Frame(root)
main_frame.pack(fill=BOTH, expand=True)

button_frame = Frame(main_frame)
button_frame.pack(side=RIGHT, padx=10, pady=10, fill=Y)

#Canvas Create + Setup
c = Canvas(main_frame,bg = "white")
c.pack(side=LEFT, fill=BOTH, expand=True)

radiovalue = StringVar()
radiovalue.set("Oval")
shape = "Pencil"

c.bind("<Button-1>", updateCoordinates)
c.bind("<B1-Motion>", createLine)
c.bind("<ButtonRelease-1>", saveDrawing)
c.bind("<Motion>", captureMotion)

#setting background color
# bg_button = Button(button_frame, text="Pick background color", command=setBgColor)
# bg_button.pack(side=TOP, padx=5, pady=10)

#setting pen color
# pen_button = Button(button_frame, text="Pick pen color", command=setPenColor)
# pen_button.pack(side=TOP, padx=5, pady=10)

#clear button
clear_button = Button(button_frame, text="Clear Button", command=clearCanvas)
clear_button.pack(side=TOP, padx=5, pady=10)

#export as image button
export_button = Button(button_frame, text="Export as Image", command=exportAsImage)
export_button.pack(side=TOP, padx=5, pady=10)

options = [
    "XY",
    "YZ",
    "ZX",
]
  
# datatype of menu text
clicked = StringVar()
var = StringVar()
  
# initial menu text
clicked.set( "XY" )
  

# Create Dropdown menu
drop = OptionMenu( root , clicked , *options )
drop.pack(side=TOP, padx=5,pady=10)
pass_label = Label(root, text="Number of Drones", font = ('calibre',10,'normal'),)
pass_label.pack()
passw_entry=Entry(root, textvariable = var, font = ('calibre',10,'normal'),)
passw_entry.pack()

radiovalue = StringVar()
radiovalue.set("Oval")

geometry_shapes = ["Pencil","Line", "Rectangle", "Arc", "Oval"]

for shape in geometry_shapes:
    radio = Radiobutton(main_frame, text=shape, variable=radiovalue, font="comicsans 12 bold",
                        value=shape, command=shapechanger).pack( padx=6, pady=3)

status = StringVar()
status.set("Position : x - 0 , y - 0")
statusbar = Label(root, textvariable=status, anchor="w", relief=SUNKEN)

statusbar.pack(side=BOTTOM, fill=X)
#Main Loop
root.mainloop()



