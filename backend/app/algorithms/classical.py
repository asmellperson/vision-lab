"""独立可调用的 OpenCV 算子。模型和专项算法由执行器另外分发。"""
import cv2
import numpy as np
from .common import Result, gray, color, binary, odd, normalize, require_image, roi_of, blank_layer, mask_layer, contours, match_pair

def run(id, im, p, extra=None):
    extra=extra or {}
    im=color(im); g=gray(im); h,w=g.shape
    data={}; layers={}; arrays={}; out=im.copy()
    if id=='pixels':
        point=(p.get('points') or [[p['x'],p['y'],1]])[-1]
        x,y=map(int,point[:2])
        if not 0<=x<w or not 0<=y<h:raise ValueError('采样点超出原图范围')
        data={'x':x,'y':y,'RGB':im[y,x,::-1].tolist(),'HSV':cv2.cvtColor(im,cv2.COLOR_BGR2HSV)[y,x].tolist(),'gray':int(g[y,x])}
        l=blank_layer(im);cv2.drawMarker(l,(x,y),(60,210,255,255),cv2.MARKER_CROSS,24,2);layers['采样点']=l
    elif id=='gray':out=g
    elif id=='color':
        codes={'RGB':cv2.COLOR_BGR2RGB,'HSV':cv2.COLOR_BGR2HSV,'Lab':cv2.COLOR_BGR2Lab,'YCrCb':cv2.COLOR_BGR2YCrCb}
        encoded=cv2.cvtColor(im,codes[p['space']]);arrays['channels']=encoded
        out=np.concatenate([cv2.cvtColor(encoded[:,:,i],cv2.COLOR_GRAY2BGR) for i in range(3)],axis=1)
        data={'space':p['space'],'display':'三个编码通道从左到右排列','ranges':[[int(encoded[:,:,i].min()),int(encoded[:,:,i].max())] for i in range(3)]}
    elif id=='channel':out=im[:,:,'BGR'.index(p['channel'])]
    elif id=='merge':out=np.clip(im.astype(float)*[p['B'],p['G'],p['R']],0,255).astype('uint8')
    elif id in ['add','subtract','blend','bit_and','bit_or','bit_xor']:
        b=require_image(extra,'reference',im)
        if id=='blend':out=cv2.addWeighted(im,p['alpha'],b,1-p['alpha'],0)
        else:out={'add':cv2.add,'subtract':cv2.subtract,'bit_and':cv2.bitwise_and,'bit_or':cv2.bitwise_or,'bit_xor':cv2.bitwise_xor}[id](im,b)
    elif id=='bit_not':out=cv2.bitwise_not(im)
    elif id=='histogram':
        out=np.full((300,512,3),20,np.uint8)
        for i,col in enumerate([(230,140,80),(90,210,110),(90,90,240)]):
            hist=cv2.calcHist([im],[i],None,[256],[0,256]).flatten(); data['BGR'[i]]=hist.astype(int).tolist()
            points=np.array([[x*2,290-int(y/(hist.max() or 1)*270)] for x,y in enumerate(hist)],np.int32)
            cv2.polylines(out,[points],False,col,2)
    elif id=='brightness':out=np.clip(im.astype(float)*p['alpha']+p['beta'],0,255).astype('uint8')
    elif id=='gamma':out=cv2.LUT(im,np.clip(255*(np.arange(256)/255)**p['gamma'],0,255).astype('uint8'))
    elif id in ['equalize','clahe']:
        lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)
        lab[:,:,0]=cv2.equalizeHist(lab[:,:,0]) if id=='equalize' else cv2.createCLAHE(p['clip'],(int(p['grid']),int(p['grid']))).apply(lab[:,:,0])
        out=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
    elif id=='mean':out=cv2.blur(im,(odd(p['kernel']),)*2)
    elif id=='gaussian':out=cv2.GaussianBlur(im,(odd(p['kernel']),)*2,0)
    elif id=='median':out=cv2.medianBlur(im,odd(p['kernel']))
    elif id=='bilateral':out=cv2.bilateralFilter(im,odd(p['kernel']),p['sigma'],p['sigma'])
    elif id=='nlm':out=cv2.fastNlMeansDenoisingColored(im,None,p['strength'],p['strength'],7,21)
    elif id=='convolution':
        m=np.asarray(p['matrix'],np.float32)
        if m.ndim!=2 or m.shape[0]!=m.shape[1] or m.shape[0]%2!=1 or m.shape[0]>15 or not np.isfinite(m).all():raise ValueError('卷积核必须是 1–15 阶有限值奇数方阵')
        out=cv2.filter2D(im,-1,m)
    elif id=='sharpen':out=cv2.addWeighted(im,1+p['amount'],cv2.GaussianBlur(im,(odd(p['kernel']),)*2,0),-p['amount'],0)
    elif id in ['fft','lowpass','highpass']:
        f=np.fft.fftshift(np.fft.fft2(g)); arrays['spectrum']=np.abs(f)
        if id=='fft':out=normalize(np.log1p(np.abs(f)))
        else:
            yy,xx=np.ogrid[:h,:w]; m=(xx-w//2)**2+(yy-h//2)**2<=(min(h,w)*p['radius'])**2
            if id=='highpass':m=~m
            out=normalize(np.abs(np.fft.ifft2(np.fft.ifftshift(f*m))))
    elif id=='threshold':out=binary(im,p['threshold'])
    elif id=='adaptive':out=cv2.adaptiveThreshold(g,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,odd(p['block']),p['constant'])
    elif id=='otsu':data['threshold'],out=cv2.threshold(g,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    elif id in ['erode','dilate','open','close','morph_gradient','tophat','blackhat']:
        shape={'ellipse':cv2.MORPH_ELLIPSE,'rect':cv2.MORPH_RECT,'cross':cv2.MORPH_CROSS}[p['shape']]
        kernel=cv2.getStructuringElement(shape,(odd(p['kernel']),)*2)
        op={'erode':cv2.MORPH_ERODE,'dilate':cv2.MORPH_DILATE,'open':cv2.MORPH_OPEN,'close':cv2.MORPH_CLOSE,'morph_gradient':cv2.MORPH_GRADIENT,'tophat':cv2.MORPH_TOPHAT,'blackhat':cv2.MORPH_BLACKHAT}[id]
        out=cv2.morphologyEx(im,op,kernel,iterations=int(p['iterations']))
    elif id=='skeleton':
        b=binary(im,p['threshold']); out=np.zeros_like(b);kernel=cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
        # 常量零边界确保全白图也会收敛。
        for _ in range(max(h,w)):
            eroded=cv2.erode(b,kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0)
            out=cv2.bitwise_or(out,cv2.subtract(b,cv2.dilate(eroded,kernel)))
            b=eroded
            if not cv2.countNonZero(b):break
    elif id=='distance':
        d=cv2.distanceTransform(binary(im,p['threshold']),cv2.DIST_L2,5);out=normalize(d);arrays['distance_pixels']=d;data['max_distance_px']=float(d.max())
    elif id in ['sobel','scharr','laplacian']:
        if id=='laplacian':out=cv2.convertScaleAbs(cv2.Laplacian(g,cv2.CV_32F))
        else:
            f=cv2.Scharr if id=='scharr' else cv2.Sobel
            out=normalize(cv2.magnitude(f(g,cv2.CV_32F,1,0),f(g,cv2.CV_32F,0,1)))
    elif id=='canny':
        if p['high']<p['low']:raise ValueError('高阈值不能低于低阈值')
        out=cv2.Canny(g,p['low'],p['high'])
    elif id in ['contours','components','hull','shape_match','count','measure']:
        mask,cs=contours(im,p['threshold'],p['min_area']);l=blank_layer(im);items=[]
        ref_cs=contours(require_image(extra,'reference'),p['threshold'],p['min_area'])[1] if id=='shape_match' else []
        if id=='shape_match' and not ref_cs:raise ValueError('参考图没有符合面积阈值的轮廓')
        centers=[]
        for i,q in enumerate(cs):
            area=float(cv2.contourArea(q));x,y,bw,bh=cv2.boundingRect(q);m=cv2.moments(q)
            cx,cy=(m['m10']/m['m00'],m['m01']/m['m00']) if m['m00'] else (x,y)
            rect=cv2.minAreaRect(q);pts=cv2.boxPoints(rect).astype('int32');centers.append([cx,cy])
            item={'id':i+1,'area_px2':area,'perimeter_px':float(cv2.arcLength(q,True)),'centroid':[cx,cy],'box':[x,y,bw,bh],'oriented_box':pts.tolist(),'width_px':rect[1][0],'height_px':rect[1][1],'angle_deg':rect[2]}
            if id=='shape_match':item['shape_distance']=float(cv2.matchShapes(q,ref_cs[0],cv2.CONTOURS_MATCH_I1,0))
            if id=='measure' and p['pixels_per_mm']>0:item.update(width_mm=rect[1][0]/p['pixels_per_mm'],height_mm=rect[1][1]/p['pixels_per_mm'])
            cv2.drawContours(l,[cv2.convexHull(q) if id=='hull' else q],-1,(80,220,100,255),2)
            if id=='measure':cv2.polylines(l,[pts],True,(255,180,60,255),2)
            cv2.circle(l,(int(cx),int(cy)),3,(60,160,255,255),-1)
            cv2.putText(l,str(i+1),(x,y+15),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255,255),1)
            items.append(item)
        layers['轮廓与标记']=l;layers['二值掩膜']=mask_layer(mask);arrays['mask']=mask;data={'count':len(items),'objects':items,'unit':'mm' if id=='measure' and p['pixels_per_mm']>0 else 'px'}
        if id=='measure':
            # 轮廓边界最近距离，而非质心间距。
            gaps=[]
            for i in range(len(cs)):
                for k in range(i+1,len(cs)):
                    from scipy.spatial import cKDTree
                    d=float(cKDTree(cs[i][:,0,:]).query(cs[k][:,0,:])[0].min());gaps.append({'pair':[i+1,k+1],'gap_px':d,**({'gap_mm':d/p['pixels_per_mm']} if p['pixels_per_mm'] else {})})
            data['gaps']=gaps
        if id=='components':
            num,labels,stats,cents=cv2.connectedComponentsWithStats(mask)
            data['components']=[{'label':i,'box':stats[i,:4].tolist(),'area_px2':int(stats[i,4]),'centroid':cents[i].tolist()} for i in range(1,num) if stats[i,4]>=p['min_area']]
            data['count']=len(data['components']);arrays['labels']=labels
    elif id=='hough_lines':
        lines=cv2.HoughLinesP(cv2.Canny(g,50,150),1,np.pi/180,int(p['votes']),minLineLength=p['length'],maxLineGap=p['gap']);l=blank_layer(im);items=[]
        if lines is not None:
            for x1,y1,x2,y2 in lines[:,0,:]:
                cv2.line(l,(x1,y1),(x2,y2),(70,220,255,255),2);items.append([int(x1),int(y1),int(x2),int(y2)])
        data['lines']=items;layers['线段']=l
    elif id=='hough_circles':
        if p['min_radius']>=p['max_radius']:raise ValueError('最大半径应大于最小半径')
        circles=cv2.HoughCircles(cv2.GaussianBlur(g,(5,5),0),cv2.HOUGH_GRADIENT,1,30,param1=100,param2=p['votes'],minRadius=int(p['min_radius']),maxRadius=int(p['max_radius']));l=blank_layer(im)
        data['circles']=[] if circles is None else circles[0].tolist()
        for x,y,r in np.round(data['circles']).astype(int):cv2.circle(l,(x,y),r,(60,210,255,255),2)
        layers['圆']=l
    elif id=='crop':
        x,y,rw,rh=roi_of(p,im);out=im[y:y+rh,x:x+rw];data['origin_offset']=[x,y]
    elif id=='resize':out=cv2.resize(im,None,fx=p['scale'],fy=p['scale'],interpolation={'nearest':0,'linear':1,'cubic':2,'area':3,'lanczos':4}[p['method']])
    elif id=='rotate':out=cv2.warpAffine(im,cv2.getRotationMatrix2D((w/2,h/2),p['angle'],1),(w,h))
    elif id=='affine':
        m=np.asarray(p['matrix'],float)
        if m.shape!=(2,3) or not np.isfinite(m).all():raise ValueError('仿射矩阵应是有限值 2×3 数组')
        out=cv2.warpAffine(im,m,(w,h))
    elif id=='perspective':
        pts=np.asarray(p.get('polygon',[]),np.float32)
        if pts.shape!=(4,2):raise ValueError('请依次选择左上、右上、右下、左下四点')
        if not cv2.isContourConvex(pts.astype('int32')) or abs(cv2.contourArea(pts))<4:raise ValueError('四点必须组成不自交的凸四边形')
        m=cv2.getPerspectiveTransform(pts,np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]));out=cv2.warpPerspective(im,m,(w,h));data['homography']=m.tolist()
    elif id in ['matching','ransac','stitch','register']:
        ref=require_image(extra,'reference');k1,k2,good,H,inliers,_,_=match_pair(im,ref,p.get('ratio',.75));data={'matches':len(good),'inliers':int(inliers.sum()),'homography':H.tolist()}
        if id in ['matching','ransac']:out=cv2.drawMatches(im,k1,ref,k2,good,None,matchesMask=inliers.ravel().tolist() if id=='ransac' else None,flags=2)
        elif id=='register':out=cv2.warpPerspective(im,H,(ref.shape[1],ref.shape[0]))
        else:
            # 根据可靠单应矩阵计算完整画布，重叠区域使用距离加权渐变融合。
            rh,rw=ref.shape[:2];corners=np.float32([[0,0],[w,0],[w,h],[0,h]])[:,None,:]
            projected=cv2.perspectiveTransform(corners,H)[:,0];all_points=np.vstack([projected,[[0,0],[rw,0],[rw,rh],[0,rh]]]);low=np.floor(all_points.min(0)).astype(int);high=np.ceil(all_points.max(0)).astype(int);ow,oh=(high-low).tolist()
            if ow<=0 or oh<=0 or ow*oh>16_000_000:raise ValueError('单应矩阵产生异常画布，请使用具有真实重叠的平面视图')
            offset=np.array([[1,0,-low[0]],[0,1,-low[1]],[0,0,1]],float)
            a=cv2.warpPerspective(im,offset@H,(ow,oh));b=cv2.warpPerspective(ref,offset,(ow,oh));ma=cv2.warpPerspective(np.ones((h,w),np.uint8),offset@H,(ow,oh));mb=cv2.warpPerspective(np.ones((rh,rw),np.uint8),offset,(ow,oh));wa=cv2.distanceTransform(ma,cv2.DIST_L2,3);wb=cv2.distanceTransform(mb,cv2.DIST_L2,3);weight=wa/(wa+wb+1e-8);out=(a*weight[:,:,None]+b*(1-weight[:,:,None])).astype('uint8');data['canvas_offset']=(-low).tolist()
    elif id=='region_grow':
        pts=p.get('points',[])
        if not pts:raise ValueError('请点选前景种子')
        x,y=map(int,pts[0][:2])
        if not 0<=x<w or not 0<=y<h:raise ValueError('种子越界')
        m=np.zeros((h+2,w+2),np.uint8);tol=p['tolerance']
        cv2.floodFill(im.copy(),m,(x,y),(0,0,0),(tol,)*3,(tol,)*3,cv2.FLOODFILL_MASK_ONLY|cv2.FLOODFILL_FIXED_RANGE|4|(255<<8));out=m[1:-1,1:-1];arrays['mask']=out
    elif id=='watershed':
        _,b=cv2.threshold(g,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU);b=cv2.morphologyEx(b,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));d=cv2.distanceTransform(b,cv2.DIST_L2,5)
        sure=(d>d.max()*p['seed_ratio']).astype('uint8');_,markers=cv2.connectedComponents(sure);markers+=1;markers[(cv2.dilate(b,None)>0)&(sure==0)]=0
        labels=cv2.watershed(im,markers);l=blank_layer(im);l[labels==-1]=(40,80,255,255);layers['分水岭边界']=l;arrays['labels']=labels;data['regions']=max(0,int(labels.max())-1)
    elif id=='grabcut':
        rect=roi_of(p,im)
        if rect==(0,0,w,h):raise ValueError('框选区域必须留出背景像素')
        m=np.zeros((h,w),np.uint8);cv2.grabCut(im,m,rect,np.zeros((1,65)),np.zeros((1,65)),int(p['iterations']),cv2.GC_INIT_WITH_RECT)
        mask=np.where((m==1)|(m==3),255,0).astype('uint8');layers['前景掩膜']=mask_layer(mask);arrays['mask']=mask
    elif id=='kmeans_segment':
        cv2.setRNGSeed(7);z=im.reshape(-1,3).astype('float32');_,labels,centers=cv2.kmeans(z,int(p['clusters']),None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,20,1),3,cv2.KMEANS_PP_CENTERS)
        out=np.uint8(centers)[labels.ravel()].reshape(im.shape);data['centers_BGR']=centers.tolist();arrays['labels']=labels.reshape(h,w)
    elif id in ['harris','shi','sift','orb']:
        maxn=int(p['max_features']);l=blank_layer(im)
        if id in ['harris','shi']:
            points=cv2.goodFeaturesToTrack(g,maxn,.01,8,useHarrisDetector=id=='harris');pts=[] if points is None else points[:,0,:].tolist()
        else:
            detector=cv2.SIFT_create(nfeatures=maxn) if id=='sift' else cv2.ORB_create(nfeatures=maxn)
            kp,desc=detector.detectAndCompute(g,None);pts=[list(k.pt) for k in kp]
            if desc is not None:arrays['descriptors']=desc
        for x,y in pts:cv2.circle(l,(int(x),int(y)),3,(80,230,180,255),1)
        layers['特征点']=l;data['keypoints']=pts;data['count']=len(pts)
    elif id=='hog':
        gx=cv2.Sobel(g,cv2.CV_32F,1,0);gy=cv2.Sobel(g,cv2.CV_32F,0,1);mag,ang=cv2.cartToPolar(gx,gy);out=np.zeros_like(im)
        cell=max(8,min(w,h)//30)
        for y in range(0,h-cell,cell):
            for x in range(0,w-cell,cell):
                hist,_=np.histogram(ang[y:y+cell,x:x+cell] % np.pi,bins=9,range=(0,np.pi),weights=mag[y:y+cell,x:x+cell]);cx,cy=x+cell//2,y+cell//2
                for k,val in enumerate(hist):
                    a=(k+.5)*np.pi/9;r=cell*.45*val/(hist.max()+1e-9);dx,dy=int(np.cos(a)*r),int(np.sin(a)*r);cv2.line(out,(cx-dx,cy-dy),(cx+dx,cy+dy),(120,220,180),1)
    elif id=='lbp':
        out=np.zeros_like(g)
        for bit,(dy,dx) in enumerate([(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]):out|=((np.roll(g,(dy,dx),(0,1))>=g).astype('uint8')<<bit)
        out[[0,-1],:]=0;out[:,[0,-1]]=0
    elif id=='template':
        if extra.get('template'):tpl=require_image(extra,'template')
        else:
            x,y,rw,rh=roi_of(p,im);tpl=im[y:y+rh,x:x+rw]
        th,tw=tpl.shape[:2]
        if th>h or tw>w:raise ValueError('模板不能大于原图')
        if float(gray(tpl).std())<1:raise ValueError('纯色模板无法使用归一化相关匹配')
        score=cv2.matchTemplate(g,gray(tpl),cv2.TM_CCOEFF_NORMED);_,best,_,loc=cv2.minMaxLoc(score);x,y=loc;l=blank_layer(im);cv2.rectangle(l,loc,(x+tw,y+th),(70,220,255,255),2);layers['匹配位置']=l;data={'score':best,'box':[x,y,tw,th]};arrays['scores']=score
    elif id in ['knn','svm','kmeans_demo']:
        rng=np.random.default_rng(42);samples=im.reshape(-1,3)[rng.choice(h*w,min(2000,h*w),replace=False)].astype('float32');features=samples[:,[2,1]];labels=(samples[:,0]>np.median(samples[:,0])).astype('int32');grid=np.float32([[x,y] for y in range(256) for x in range(256)])
        if len(np.unique(labels))<2 and id!='kmeans_demo':raise ValueError('蓝通道变化不足，无法构造两类教学样本')
        if id=='knn':model=cv2.ml.KNearest_create();model.train(features,cv2.ml.ROW_SAMPLE,labels);_,pred,_,_=model.findNearest(grid,int(p['complexity']))
        elif id=='svm':model=cv2.ml.SVM_create();model.setKernel(cv2.ml.SVM_RBF);model.setC(p['complexity']);model.setGamma(.0001);model.train(features,cv2.ml.ROW_SAMPLE,labels);_,pred=model.predict(grid)
        else:
            cv2.setRNGSeed(42);_,_,centers=cv2.kmeans(features,max(2,int(p['complexity'])),None,(3,30,.2),3,cv2.KMEANS_PP_CENTERS);pred=np.argmin(((grid[:,None]-centers[None])**2).sum(2),axis=1)
        palette=np.array([[70,90,160],[100,160,65],[160,100,65],[120,65,160],[65,160,160]]*2,np.uint8);out=palette[pred.astype(int).ravel()].reshape(256,256,3)
        for xy,lab in zip(features[:300],labels[:300]):cv2.circle(out,tuple(xy.astype(int)),2,(240,240,240) if lab else (20,20,20),-1)
        data={'training_samples':len(samples),'features':['R','G'],'labels':'B 大于样本中位数的教学标签','note':'无独立真值，不报告准确率'}
    elif id=='lowlight':
        f=im.astype('float32')+1;ret=np.log(f)-np.log(cv2.GaussianBlur(f,(0,0),p['sigma']));out=normalize(ret)
    elif id=='inpaint':
        pts=p.get('mask_points',[])
        if not pts:raise ValueError('请在原图绘制需要修复的掩膜')
        m=np.zeros((h,w),np.uint8)
        for point in pts:
            x,y,r=map(int,point);cv2.circle(m,(x,y),max(1,min(r,100)),255,-1)
        out=cv2.inpaint(im,m,p['radius'],cv2.INPAINT_TELEA);arrays['mask']=m
    elif id=='augmentation':
        out=cv2.warpAffine(im,cv2.getRotationMatrix2D((w/2,h/2),p['angle'],1),(w,h))
        if p['flip']!='none':out=cv2.flip(out,1 if p['flip']=='horizontal' else 0)
        noise=np.random.default_rng(42).normal(0,p['noise'],out.shape);out=np.clip(out*p['brightness']+noise,0,255).astype('uint8')
    elif id in ['qr','barcode']:
        l=blank_layer(im);items=[]
        if id=='qr':
            ok,texts,points,_=cv2.QRCodeDetector().detectAndDecodeMulti(im);types=['QR']*len(texts)
        else:
            if not hasattr(cv2,'barcode_BarcodeDetector'):raise ValueError('需要 opencv-contrib-python-headless 的 barcode 模块')
            ok,texts,types,points=cv2.barcode_BarcodeDetector().detectAndDecodeWithType(im)
        if ok and points is not None:
            for s,typ,pts in zip(texts,types,points):items.append({'text':s,'type':typ,'polygon':pts.tolist()});cv2.polylines(l,[pts.astype('int32')],True,(60,220,160,255),2)
        layers['码位置']=l;data['codes']=items
    else:
        from .special import run as special_run
        return special_run(id,im,p,extra)
    return Result(out,data,layers,arrays)
