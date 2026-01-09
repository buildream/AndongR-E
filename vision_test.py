import numpy as np
import cv2

img=cv2.imread('qcentor.jpg')
while(1):
    cv2.imshow('rgb',img)
    red=img[:,:,2]
    green=img[:,:,1]
    blue=img[:,:,0]

    cv2.imshow('red',red)
    cv2.imshow('gree',green)
    cv2.imshow('blue',blue)
    red_only=np.int16(red)-np.int16(green)

    red_only[red_only<0]=0
    red_only[red_only>255]=255
    red_only0=np.uint8(red_only)
    _, red_only = cv2.threshold(red_only0, 80, 255, cv2.THRESH_BINARY)

    cv2.imshow('red_only',red_only)
    x,y=np.shape(red_only)
    col_sums=np.matrix(np.sum(red_only,0))
    col_nums=np.matrix(np.arange(y))
    col_mult=np.multiply(col_sums,col_nums)
    total=np.sum(col_mult)
    total_total=np.sum(np.sum(red_only))
    col_loc=total/total_total

    row_sums=np.matrix(np.sum(red_only,1))
    row_nums=np.matrix(np.arange(x))
    row_mult=np.multiply(row_sums,row_nums)
    total2=np.sum(row_mult)
    row_loc=total2/total_total

    result=red_only0
    cv2.circle(result,(np.int32(col_loc),np.int32(row_loc)),10,(0,0,0),2,cv2.LINE_AA)
    cv2.imshow('result',result)
    print(col_loc,row_loc)
    
    k=cv2.waitKey(5)
    if k==27:
        break
cv2.destroyAllWindows()

