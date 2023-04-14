import cv2
import numpy as np
import copy
import pandas as pd
import json 

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
    _,thresh = cv2.threshold(imggray,127,255,cv2.THRESH_BINARY_INV) 

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
    
    


try:
    #######
    # Keep it within Try except block - Ek remark ka text field bana dena GUI mein
    #  and usme exception ka message print karwa dena if any error occurs
    #
    # Ye implement kar dena as Text field as predefined values
    #  
    # input parameters
    #File path
    #Number of Vertices
    #Name of file to be saved
    #Plane
    #hyp_area=0.2,
    # delta=5
    # eps=0.01
    # eps_increment=0.005
    generate_coordinates("india.jpeg",80,filename="coordinates.txt",plane='yz',hyp_area=0.2,delta=5, eps=0.01,eps_increment=0.005)
except: 
    print("""Overcrowed -
          1) Reduce the Number of points
          2) Increase image size""")