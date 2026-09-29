"""工业规则、相机几何、点云与有真值评估。"""
import cv2
import numpy as np
from scipy.spatial import cKDTree
from .common import Result, gray, normalize, require_image, roi_of, blank_layer, mask_layer, read_image, match_pair

def run(id,im,p,extra):
    h,w=im.shape[:2];data={};layers={};arrays={};out=im.copy()
    if id in ['color_check','difference','assembly','defects']:
        if id=='defects':ref=cv2.GaussianBlur(im,(0,0),7)
        else:ref=require_image(extra,'reference',im)
        diff=cv2.absdiff(im,ref);score=gray(diff);m=(score>p['sensitivity']).astype('uint8')*255
        layers['差异区域']=mask_layer(m,(60,70,240));arrays['difference']=diff;arrays['mask']=m
        data={'mean_abs_difference':float(diff.mean()),'changed_fraction':float((m>0).mean()),'method':'局部平滑残差规则' if id=='defects' else '已对齐参考图差异规则'}
        if id=='color_check':
            a=cv2.cvtColor(im.astype('float32')/255,cv2.COLOR_BGR2LAB);b=cv2.cvtColor(ref.astype('float32')/255,cv2.COLOR_BGR2LAB)
            delta=np.linalg.norm(a-b,axis=2);data.update(mean_Lab=a.mean((0,1)).tolist(),reference_Lab=b.mean((0,1)).tolist(),mean_deltaE76=float(delta.mean()));arrays['deltaE76']=delta
        if id=='assembly':
            regions=p['regions'] or [roi_of(p,im)];data['regions']=[]
            for q in regions:
                x,y,rw,rh=roi_of({'roi':q},im);d=float(score[y:y+rh,x:x+rw].mean());data['regions'].append({'roi':[x,y,rw,rh],'difference':d,'pass':d<=p['sensitivity']})
            data['pass']=all(r['pass'] for r in data['regions'])
    elif id=='calibrate':
        paths=extra.get('calibration_images',[])
        if len(paths)<5:raise ValueError('至少上传 5 张同一相机、不同视角的棋盘格图；建议 10–20 张')
        cols,rows=int(p['cols']),int(p['rows']);obj=np.zeros((rows*cols,3),np.float32);obj[:,:2]=np.mgrid[0:cols,0:rows].T.reshape(-1,2)*p['square_mm'];objs=[];points=[];used=[]
        for path in paths:
            image=read_image(path)
            if image.shape[:2]!=(h,w):raise ValueError('所有标定图必须与主图分辨率一致')
            found,corners=cv2.findChessboardCornersSB(gray(image),(cols,rows))
            if found:objs.append(obj);points.append(corners);used.append(str(path.name))
        if len(points)<5:raise ValueError(f'只有 {len(points)} 张成功检测棋盘内角点，至少需要 5 张')
        error,K,D,rvecs,tvecs=cv2.calibrateCamera(objs,points,(w,h),None,None)
        out=cv2.undistort(im,K,D);data={'camera':K.tolist(),'distortion':D.ravel().tolist(),'rms_reprojection_px':error,'image_size':[w,h],'used':used,'square_mm':p['square_mm']}
    elif id=='undistort':
        K=np.asarray(p['camera'],float);D=np.asarray(p['distortion'],float)
        if K.shape!=(3,3) or K[0,0]<=0 or K[1,1]<=0 or D.size not in [4,5,8,12,14]:raise ValueError('无效相机矩阵或畸变参数')
        out=cv2.undistort(im,K,D);data={'camera':K.tolist(),'distortion':D.tolist()}
    elif id=='stereo_rectify':
        ref=require_image(extra,'reference',im);cal=p['calibration']
        if any(k not in cal for k in ['K1','D1','K2','D2','R','T']):raise ValueError('双目标定需 K1,D1,K2,D2,R,T，T 的单位决定输出尺度')
        K1,D1,K2,D2,R,T=[np.asarray(cal[k],float) for k in ['K1','D1','K2','D2','R','T']]
        R1,R2,P1,P2,Q,_,_=cv2.stereoRectify(K1,D1,K2,D2,(w,h),R,T)
        m1=cv2.initUndistortRectifyMap(K1,D1,R1,P1,(w,h),cv2.CV_32FC1);m2=cv2.initUndistortRectifyMap(K2,D2,R2,P2,(w,h),cv2.CV_32FC1)
        left=cv2.remap(im,*m1,cv2.INTER_LINEAR);right=cv2.remap(ref,*m2,cv2.INTER_LINEAR);out=np.hstack([left,right]);arrays.update(left=left,right=right);data['Q']=Q.tolist()
    elif id=='stereo':
        ref=require_image(extra,'reference',im);nd=int(np.ceil(p['disparities']/16)*16);bs=int(p['block'])|1
        if w<=nd+bs:raise ValueError('图像宽度必须大于视差搜索范围')
        matcher=cv2.StereoSGBM_create(minDisparity=0,numDisparities=nd,blockSize=bs,P1=8*bs*bs,P2=32*bs*bs,uniquenessRatio=10,speckleWindowSize=50,speckleRange=2)
        disparity=matcher.compute(gray(im),gray(ref)).astype('float32')/16;valid=disparity>0
        arrays['disparity_px']=disparity;out=cv2.applyColorMap(normalize(np.maximum(disparity,0)),cv2.COLORMAP_TURBO);data={'valid_fraction':float(valid.mean()),'scale':'像素视差；输入必须已极线校正'}
        if p['focal']>0 and p['baseline']>0:
            depth=np.full_like(disparity,np.nan);depth[valid]=p['focal']*p['baseline']/disparity[valid];arrays['depth_mm']=depth;data['scale']='毫米，依赖给定焦距与基线及有效双目标定'
    elif id=='reconstruct':
        ref=require_image(extra,'reference');K=np.asarray(p['camera'],float);K2=np.asarray(p['camera_reference'],float)
        if K.shape!=(3,3) or K2.shape!=(3,3):raise ValueError('相机内参应为 3×3 矩阵')
        _,_,_,_,_,pts1,pts2=match_pair(im,ref)
        if len(pts1)<8:raise ValueError('重建至少需要 8 个可靠匹配')
        pts1=cv2.undistortPoints(pts1[:,None,:],K,None)[:,0];pts2=cv2.undistortPoints(pts2[:,None,:],K2,None)[:,0]
        E,mask=cv2.findEssentialMat(pts1,pts2,np.eye(3),method=cv2.RANSAC,threshold=1/max(K[0,0],K2[0,0]))
        if E is None:raise ValueError('无法估计本质矩阵')
        count,R,T,mask=cv2.recoverPose(E[:3],pts1,pts2,np.eye(3),mask=mask)
        if count<8:raise ValueError('可三角化的正深度对应点不足；纯旋转或平面退化无法可靠重建')
        ok=mask.ravel()>0;pts1,pts2=pts1[ok],pts2[ok]
        points=cv2.triangulatePoints(np.hstack([np.eye(3),np.zeros((3,1))]),np.hstack([R,T]),pts1.T,pts2.T);xyz=(points[:3]/points[3]).T
        xyz=xyz[np.isfinite(xyz).all(1)&(xyz[:,2]>0)];arrays['points']=xyz;data={'points':xyz[:10000].tolist(),'rotation':R.tolist(),'translation_relative':T.ravel().tolist(),'scale':'相对尺度，无法直接测量毫米','count':len(xyz)}
    elif id.startswith('eval_'):
        data=evaluate(id,p.get('annotations',p),im,extra)
    else:raise ValueError(f'未找到执行器：{id}')
    return Result(out,data,layers,arrays)

def evaluate(id,annotations,im,extra):
    if id=='eval_segmentation':
        if annotations.get('mode')=='multiclass':
            truth=gray(require_image(extra,'truth_mask',im));pred=gray(im);valid=truth!=annotations.get('ignore_label',255)
            if not valid.any():raise ValueError('所有真值像素均被忽略，无法计算指标')
            classes=np.union1d(truth[valid],pred[valid]);rows=[]
            for cls in classes:
                a=(truth==cls)&valid;b=(pred==cls)&valid;intersection=int((a&b).sum());union=int((a|b).sum());den=int(a.sum()+b.sum());rows.append({'class_id':int(cls),'IoU':intersection/union if union else 1.,'Dice':2*intersection/den if den else 1.,'truth_pixels':int(a.sum())})
            return {'mIoU':float(np.mean([q['IoU'] for q in rows])),'mean_Dice':float(np.mean([q['Dice'] for q in rows])),'pixel_accuracy':float((truth[valid]==pred[valid]).mean()),'classes':rows,'note':'均值包含背景类别；忽略真值 ignore_label 像素'}
        truth=gray(require_image(extra,'truth_mask',im))>127;pred=gray(im)>127
        intersection=int((truth&pred).sum());union=int((truth|pred).sum());den=int(truth.sum()+pred.sum())
        return {'IoU':intersection/union if union else 1.,'Dice':2*intersection/den if den else 1.,'pixel_accuracy':float((truth==pred).mean()),'task':'二值分割，主图为预测掩膜，专用输入为真值掩膜'}
    truth=annotations.get('truth');prediction=annotations.get('prediction')
    if not isinstance(truth,list) or not isinstance(prediction,list):raise ValueError('JSON 需要 truth 和 prediction 两个数组；详情见 README')
    if id=='eval_classification':
        if not truth or len(truth)!=len(prediction):raise ValueError('分类真值与预测必须等长且非空')
        classes=sorted(set(map(str,truth+prediction)));index={c:i for i,c in enumerate(classes)};cm=np.zeros((len(classes),len(classes)),int)
        for a,b in zip(truth,prediction):cm[index[str(a)],index[str(b)]]+=1
        tp=np.diag(cm);precision=np.divide(tp,cm.sum(0),out=np.zeros(len(classes),float),where=cm.sum(0)>0);recall=np.divide(tp,cm.sum(1),out=np.zeros(len(classes),float),where=cm.sum(1)>0);f1=np.divide(2*precision*recall,precision+recall,out=np.zeros(len(classes),float),where=(precision+recall)>0)
        return {'accuracy':float(tp.sum()/cm.sum()),'classes':classes,'confusion_matrix':cm.tolist(),'precision':precision.tolist(),'recall':recall.tolist(),'macro_F1':float(f1.mean())}
    # COCO 风格 101 点插值 AP，按图像和类别一对一匹配，不冒充完整 COCO evaluator。
    for obj in truth+prediction:
        if not all(k in obj for k in ['image_id','class_id','box']):raise ValueError('检测对象需 image_id、class_id、box=[x1,y1,x2,y2]；预测还需 score')
        if len(obj['box'])!=4 or obj['box'][2]<=obj['box'][0] or obj['box'][3]<=obj['box'][1]:raise ValueError('检测框坐标必须有效且面积为正')
    if not truth:raise ValueError('计算 AP 至少需要一个有标注目标')
    if any('score' not in x for x in prediction):raise ValueError('每个预测框都必须提供 score')
    scores={}
    for threshold in np.arange(.5,1,.05):
        aps=[]
        for cls in set(str(x['class_id']) for x in truth):
            gt=[x for x in truth if str(x['class_id'])==cls];pred=sorted([x for x in prediction if str(x['class_id'])==cls],key=lambda x:x['score'],reverse=True);matched=set();tp=[]
            for q in pred:
                candidates=[(box_iou(q['box'],g['box']),i) for i,g in enumerate(gt) if i not in matched and g['image_id']==q['image_id']]
                best,idx=max(candidates,default=(0,-1));hit=best>=threshold
                if hit:matched.add(idx)
                tp.append(int(hit))
            cumulative=np.cumsum(tp);recall=cumulative/len(gt);precision=cumulative/np.arange(1,len(tp)+1)
            ap=np.mean([float(precision[recall>=r].max()) if np.any(recall>=r) else 0 for r in np.linspace(0,1,101)]);aps.append(ap)
        scores[f'{threshold:.2f}']=float(np.mean(aps))
    return {'AP50':scores['0.50'],'mAP50_95':float(np.mean(list(scores.values()))),'AP_by_IoU':scores,'method':'101 点插值 AP；不含 COCO crowd / area / maxDets 子集规则'}

def box_iou(a,b):
    x1,y1=max(a[0],b[0]),max(a[1],b[1]);x2,y2=min(a[2],b[2]),min(a[3],b[3]);intersection=max(0,x2-x1)*max(0,y2-y1)
    return intersection/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)

def read_cloud(path):
    """支持纯文本 XYZ/CSV 和 ASCII PLY；拒绝二进制格式而不错误解释。"""
    lines=path.read_text().splitlines();start=0
    if lines and lines[0].strip()=='ply':
        if 'format ascii 1.0' not in lines[:10]:raise ValueError('目前只支持 ASCII PLY，请先转换二进制点云')
        start=lines.index('end_header')+1
        count=int(next(x.split()[-1] for x in lines if x.startswith('element vertex ')))
        lines=lines[start:start+count]
    points=np.array([[float(v) for v in line.replace(',',' ').split()[:3]] for line in lines if line.strip() and not line.startswith('#')],np.float64)
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():raise ValueError('点云应是每行三个有限数值 x y z')
    if len(points)>500000:raise ValueError('点云上限为 50 万点，请先下采样')
    return points

def pointcloud(path,p,extra):
    xyz=read_cloud(path);data={}
    if p['voxel']>0:
        _,idx=np.unique(np.floor(xyz/p['voxel']),axis=0,return_index=True);xyz=xyz[idx]
    if not len(xyz):raise ValueError('点云为空')
    if p['operation']=='plane':
        if len(xyz)<3:raise ValueError('平面拟合至少需要 3 点')
        rng=np.random.default_rng(42);best=np.zeros(len(xyz),bool);plane=None
        for _ in range(100):
            a,b,c=xyz[rng.choice(len(xyz),3,replace=False)];normal=np.cross(b-a,c-a);norm=np.linalg.norm(normal)
            if norm<1e-9:continue
            normal/=norm;d=-normal@a;mask=np.abs(xyz@normal+d)<p['distance']
            if mask.sum()>best.sum():best=mask;plane=[*normal.tolist(),float(d)]
        data.update(plane=plane,inlier_count=int(best.sum()),inlier_indices=np.flatnonzero(best)[:20000].tolist())
    elif p['operation']=='register':
        if not extra.get('reference_cloud'):raise ValueError('点云配准需要第二份 reference_cloud')
        target=read_cloud(extra['reference_cloud'][0]);tree=cKDTree(target);transform=np.eye(4)
        for _ in range(30):
            distance,idx=tree.query(xyz);keep=distance<=np.quantile(distance,.8);a=xyz[keep];b=target[idx[keep]]
            if len(a)<3:raise ValueError('有效对应点不足')
            ac,bc=a.mean(0),b.mean(0);u,_,vt=np.linalg.svd((a-ac).T@(b-bc));R=vt.T@u.T
            if np.linalg.det(R)<0:vt[-1]*=-1;R=vt.T@u.T
            t=bc-R@ac;xyz=xyz@R.T+t;step=np.eye(4);step[:3,:3]=R;step[:3,3]=t;transform=step@transform
        data.update(transform=transform.tolist(),rmse=float(np.sqrt(np.mean(tree.query(xyz)[0]**2))),method='点到点 ICP，需要近似初始对齐')
    # 返回可旋转显示的数据及静态 XY 投影下载。
    data.update(points=xyz[np.linspace(0,len(xyz)-1,min(len(xyz),20000),dtype=int)].tolist(),count=len(xyz),unit='与输入点云一致')
    canvas=np.full((640,640,3),24,np.uint8);xy=xyz[:,:2];span=np.ptp(xy,axis=0);pixels=((xy-xy.min(0))/(span+1e-9)*590+25).astype(int)
    for x,y in pixels:cv2.circle(canvas,(x,639-y),1,(190,210,70),-1)
    return Result(canvas,data,arrays={'points':xyz})
