import cv2
import numpy as np
import copy
import pandas as pd
import json 
import tkinter.messagebox as alert
from tkinter import *
from tkinter import messagebox, filedialog, Menu
from PIL import Image, ImageDraw, ImageGrab

old_x, old_y = 0, 0
pen_color = "black"
bg_color = "white"
number_of_drones = 80
axis = "yz"
created = []
new = []
created_element_info = []

#Calculates area of triangle
def areaoftri(p1, p2, p3):
    return abs(p1[0]*(p2[1]-p3[1])+p2[0]*(p3[1]-p1[1])+p3[0]*(p1[1]-p2[1]))/2.

#Generates coordinates for the given closed contour
def getboundary(num_of_vertices,contours,delta=5, eps=0.01,eps_increment=0.005):
        #Skip the situations who has <=1 coordinates
        if(contours.shape[0] <= 1):
                return []
        
        #For 0,1,2 num_of_vertices we simply apply RDP algo until we get 2 points
        #If 1 point is asked we return the first point from the 2 set
        if(num_of_vertices < 3):
            eps_increment = eps_increment
            approx = contours
            
            while(len(approx) != 2):  
                approx = cv2.approxPolyDP(contours,eps,True)
                eps += eps_increment 
            approx = approx.reshape(len(approx),2)
            
            if(num_of_vertices == 1):
                return [approx[0]]
            elif(num_of_vertices == 2):
                return approx
            else:
                return []

        #Here we apply RDP algo until we reach near num_of_vertices
        #The reason is it is much faster than Visvalingam-Whyatt method
        #We keep on incrementing eps until we get close to num_of_vertices
        #The closeness is defined by delta
        approx = np.zeros(num_of_vertices+delta)
        while(len(approx) >= num_of_vertices + delta):   
            approx = cv2.approxPolyDP(contours,eps,True)
            eps += eps_increment 
        else:
            #To avoid situation where len approx becomes less than number of vertices
            #So increase the size of approx

            if(len(approx) < num_of_vertices):
                try:
                    while(len(approx) < num_of_vertices):
                        eps -= eps_increment 
                        approx = cv2.approxPolyDP(contours,eps,True)
                except:
                    approx = contours
                    
                    
        #Further this is modified version of Visvalingam-Whyatt
        #Here we don't use eps_area instead I remove the area
        #that has minimum area. This ensures the removal of the
        #least important point

        #Areainfo contains the information about all the area formed
        # with consecutive points 
        areainfo = np.zeros(len(approx)-2)
        approx = approx.reshape(len(approx),2)
        #Calculate the area
        for i in range(1, len(approx)-2):
            p1 = approx[i-1]
            p2 = approx[i]
            p3 = approx[i+1]
            areainfo[i] = areaoftri(p1,p2,p3)

        #We delete the min area and repeat it until the desired num_of_vertices 
        #is not reached
        while(len(approx) != num_of_vertices):
            #Get minimum area index
            min_area_index = np.argmin(areainfo)
            areainfo = np.delete(areainfo, min_area_index)
            approx = np.delete(approx, min_area_index+1,axis=0)
            #2 situations arise for 1st and last points and for any intermediate point
            if(min_area_index == 0):
                p1 = approx[1]
                p2 = approx[2]
                p3 = approx[0]
                areainfo[0] = areaoftri(p1,p2,p3)
            elif(min_area_index == len(areainfo)):
                p1 = approx[min_area_index+1]
                p2 = approx[min_area_index]
                p3 = approx[min_area_index-1]
                areainfo[min_area_index-1] = areaoftri(p1,p2,p3)
            else:
                p1 = approx[min_area_index+1]
                p2 = approx[min_area_index]
                p3 = approx[min_area_index-1]
                areainfo[min_area_index-1] = areaoftri(p1,p2,p3)

                p3 = approx[min_area_index+2]
                areainfo[min_area_index] = areaoftri(p2,p1,p3)
        
        return approx

def save(filename, coord, plane, shape):
    if(not(filename)):
        return
    finaldf = pd.DataFrame(columns=['X','Y','Z']) 
    for i in coord:
        try:
            df = pd.DataFrame({'X': i[:,0],
                            'Y': i[:,1],
                            'Z':np.zeros(len(i))})
            finaldf = pd.concat([finaldf,df])
        except:
            pass
    
    
    if(plane.lower() == 'xy'):
        pass
    elif(plane.lower() == 'yz'):
        min_y = df['Y'].min()
        max_y = df['Y'].max()
        min_x = df['X'].min()
        max_x = df['X'].max()

        df['Y'].apply(lambda y: max_y + min_y - y)
        df['X'].apply(lambda x: max_x + min_x - x)
        df.columns = ["Y", "Z", "X"]
        cols = ["X","Y","Z"]
        df = df.loc[:,cols]
    else:
        min_y = df['Y'].min()
        max_y = df['Y'].max()
        df['Y'].apply(lambda y: max_y + min_y - y)
        df.columns = ["X", "Z", "Y"]
        cols = ["X","Y","Z"]
        df = df.loc[:,cols]

    with open(filename, 'w') as f:
        f.write(str(shape[:-1])+'\n')
        dfAsString = df.to_string(header=True, index=False)
        f.write(dfAsString)
   
    dict = {}
    dict["screen_size"] = {"x": shape[0], "y": shape[1]}
    for i in range(len(df['X'])):
        data = df.iloc[i]
        dict[f"drone{i+1}"] = {"x" : data[0], "y": data[1], "z": data[2]}

    json_fn = filename.split()[0] + '.json'  
    with open(json_fn,'w') as f:
        json.dump(dict, f, indent=4)

def generate_coordinates(path,total_num_of_vertices,plane='xy',filename=None,hyp_area=0.2,delta=5, eps=0.01,eps_increment=0.005):
    #Read image
    img = cv2.imread(path)
    cv2.imshow('orig', img)
    #object to be found should be white and background should be black.
    imggray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)                 #Converted to Grayscale
    if(imggray[0][0] == 255):
        _,thresh = cv2.threshold(imggray,127,255,cv2.THRESH_BINARY_INV) 
    else:
         _,thresh = cv2.threshold(imggray,127,255,cv2.THRESH_BINARY) 

    #Closing required to omit noise contours. Fills any hole or broken part
    #Opening is not suitable as it would completely making the image disappear
    thresh = cv2.dilate(thresh, None, iterations=1)
    thresh = cv2.erode(thresh,None,iterations=1)

    #Find all possible contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

    #Extraction of important contours
    #Created Bounding box around each closed contour and checked if area 
    #of any closed contour is less than hyp_area(=20%). If yes removed that contour
    # as they are redundant 
    mod_contours = list(copy.deepcopy(contours))
    #Stores area of all contours
    area_of_all_contours = [cv2.contourArea(cont) for cont in contours]
    upperlimit  = len(contours)
    dellist = []
    for i,cnt in enumerate(contours):
        #Skipped the contours that are already in dellist 
        if(i in dellist):
            continue
        
        #Get bounding box around the closed contour which is under consideration
        x,y,w,h = cv2.boundingRect(cnt)
        #Area of the contour which is under consideration
        max_area = area_of_all_contours[i]
        #loop through all contours that have the possibility to be within than bounding box
        for j in range(i+1,upperlimit):
            #Create bounding box within the children contours
            x_,y_,w_,h_ = cv2.boundingRect(contours[j])

            #Check if the bounding box is within the parent
            #Condition for the bb to be inside the bigger bounding box
            condition = x_ >= x and y_>=y and w_<=w and h_ <= h
            #Area under the children contour
            considered_area = area_of_all_contours[j]

            #Condition for noise boundaries to be omitted
            #condition2 = considered_area < 10 #Not implemented-Solved through closing
            #You can also consider perimeter with area
            #If the diff between parent and children area is < hyp_area it would be
            #considered redundant and deleted
            if( condition and 1-(considered_area/max_area) < hyp_area):
                dellist.append(j)

    #Deleting all the redundant contours
    for i in sorted(dellist, reverse=True):
        del mod_contours[i]
        del area_of_all_contours[i]

    #OpenCV convetion for contours to be tuple
    contours = tuple(mod_contours)

    #Get all the perimeter- Area did not work well
    #Using this perimeter we will distribute num_of_vertices for each of the contour detected
    perimeter_of_all_contours = [cv2.arcLength(cnt,True) for cnt in contours]
    num_of_vertices_contourwise = []
    for i,key in enumerate(perimeter_of_all_contours):
        #No of vertices distributed as fraction of its perimeter out of total perimeter
        val = int(key/sum(perimeter_of_all_contours) * total_num_of_vertices)
        num_of_vertices_contourwise.append(val)
    else:
        try:
        #This is done in order to keep the total sum as given no of vertices
            num_of_vertices_contourwise[i] = total_num_of_vertices - sum(num_of_vertices_contourwise[:-1])
        except:
            print('No outline detected')

    #All coord will store all the coordinates for each of the contours
    all_coord = []
    diff = 0
    for j in range(len(contours)):
        #There are certain situations where contour length is smaller than the num of vertices assigned 
        #to that contour so passed those extra contour numbers to the one with the biggest perimeter
        if(contours[j].shape[0] < num_of_vertices_contourwise[j]):
            diff = num_of_vertices_contourwise[j] - contours[j].shape[0]
            num_of_vertices_contourwise[j] = contours[j].shape[0]
            ind = num_of_vertices_contourwise.index(max(num_of_vertices_contourwise))
            num_of_vertices_contourwise[ind] += diff 
        #Gets the coordinates corresponding to that contour
        approx = getboundary(num_of_vertices_contourwise[j],contours[j],delta, eps,eps_increment)
        all_coord.append(approx)
    else:
        #If diff is non-zero we again apply the algo to get new set of coordinates for the largest perimeter
        if(diff):
            approx =  getboundary(num_of_vertices_contourwise[0],contours[0],delta, eps,eps_increment)  
            all_coord[0] = approx
    save(filename, all_coord,plane, img.shape)

    #Uncomment to display image
    trialimage = np.zeros(img.shape[:-1],dtype=np.uint8) 
    finalimage = thresh.copy()

    for approx in all_coord: 
        for i in approx:
                finalimage = cv2.circle(finalimage, i, radius=3, color=(150, 150, 150), thickness=-1)
                trialimage = cv2.circle(trialimage, i, radius=3, color=(255, 255, 255), thickness=-1)
    cv2.imshow('final', finalimage)
    cv2.imshow('sa', trialimage)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def updateCoordinates(event):
    global old_x, old_y
    print("Called!!!!")
    old_x, old_y = event.x, event.y
    print(old_x,old_y)

def addLine(event):
    global old_x, old_y
    c.create_line((old_x, old_y, event.x, event.y), fill=pen_color)
    old_x, old_y = event.x, event.y

def upddateCoordinated(value):
    global number_of_drones
    number_of_drones = value

def updateAxis(value):
    global axis
    axis = value

def clearCanvas():
    c.delete("all")

#Works for whole frame
# def exportAsImage():
#     filename = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg'), ('GIF', '*.gif')], title="Save the image as...")
#     main_frame.update()
#     x = root.winfo_rootx() + main_frame.winfo_x()
#     y = root.winfo_rooty() + main_frame.winfo_y()
#     width = main_frame.winfo_width()
#     height = main_frame.winfo_height()

#     img = ImageGrab.grab(bbox=(x, y, x+width, y+height))
#     img.save(filename)
#     print("Image saved as '{filename}")
#     messagebox.showinfo("Export as image", f"Image exported successfully to '{filename}'")


def createElms():
    global shape, old_x,old_y
    if shape == "Rectangle":
        a = c.create_rectangle(old_x, old_y, x, y,activewidth=2,outline='black')
    elif shape == "Oval":
        print("Oval Called")
        print(shape)
        a = c.create_oval(old_x, old_y, x, y,activewidth=2,outline='black')
    elif shape == "Polygan":
        a = c.create_polygon(
            old_x, old_y, x, y, old_x, old_y,activewidth=2,outline='black')
    elif shape == "Arc":
        a = c.create_arc(old_x, old_y, x, y,activewidth=2,outline='black')
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

def exportkarImage():
    filename = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg'), ('GIF', '*.gif')], title="Save the image as...")
    main_frame.update()
    x = root.winfo_rootx() + main_frame.winfo_x()
    y = root.winfo_rooty() + main_frame.winfo_y()
    width = main_frame.winfo_width()
    height = main_frame.winfo_height()

    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # draw the white canvas
    draw.rectangle((0, 0, width, height), fill=bg_color)

    # draw the lines
    for item in c.find_all():
        if c.type(item) == "line":
            coords = c.coords(item)
            draw.line([(coords[i], coords[i+1]) for i in range(0, len(coords), 2)], fill=pen_color, width=2)

        elif c.type(item) == "rectangle":
            coords = c.coords(item)
            draw.rectangle(coords, outline=pen_color, width=2)

        elif c.type(item) == "oval":
            coords = c.coords(item)
            draw.ellipse(coords, outline=pen_color, width=2)

        elif c.type(item) == "arc":
            coords = c.coords(item)
            draw.arc(coords, outline=pen_color, width=2)

        elif c.type(item) == "polygon":
            coords = c.coords(item)
            draw.polygon(coords, outline=pen_color, width=2)

    img = img.crop((0, 0, width, height))
    img.save(filename)
    print(f"Image saved as '{filename}")
    messagebox.showinfo("Export as image", f"Image exported successfully to '{filename}'")
    
    try:
        print(number_of_drones)
        print(axis)
        generate_coordinates(filename,50,filename="coordinates.txt",plane='yz',hyp_area=0.2,delta=5, eps=0.01,eps_increment=0.005)
    except: 
        print("""Overcrowed -
            1) Change the Number of points
            2) Increase image size""")

#Root Create + Setups
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
c.itemconfig(c.find_all(), tags=("bg",))

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
export_button = Button(button_frame, text="Export as Image", command=exportkarImage)
export_button.pack(side=TOP, padx=5, pady=10)

#export as image button
# upload_button = Button(button_frame, text="Export as Image", command=exportkarImage)
# upload_button.pack(side=TOP, padx=5, pady=10)

options = [
    "YZ",
    "XY",
    "ZX",
]
  
# datatype of menu text
clicked = StringVar()
var = StringVar()
  
# initial menu text
clicked.set( "YZ" )
  

# Create Dropdown menu
pass_label = Label(main_frame, text="Update the axis", font = ('calibre',10,'normal'),)
pass_label.pack()
drop = OptionMenu( main_frame , clicked , *options )
drop.pack(side=TOP, padx=5,pady=10)
pass_label = Label(main_frame, text="Number of Drones", font = ('calibre',10,'normal'),)
pass_label.pack()
passw_entry=Entry(main_frame, textvariable = var, font = ('calibre',10,'normal'),)
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





    
