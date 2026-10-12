"""Ручное чтение метаданных изображений без Pillow/Image/System.Drawing."""
from __future__ import annotations
import os, struct
from dataclasses import dataclass, asdict
from typing import Optional

SUPPORTED = {'.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.bmp', '.png', '.pcx'}

@dataclass
class ImageInfo:
    filename: str
    path: str
    format: str = 'Неизвестен'
    dimensions: str = '—'
    resolution: str = '—'
    color_depth: str = '—'
    compression: str = '—'
    status: str = 'OK'
    file_size: str = '—'
    details: str = ''

class ParseError(Exception): pass

def _read_exact(f, n):
    b=f.read(n)
    if len(b)!=n: raise ParseError('Недостаточно данных: заголовок обрезан')
    return b

def _u16(b, endian='<'): return struct.unpack(endian+'H', b)[0]
def _u32(b, endian='<'): return struct.unpack(endian+'I', b)[0]
def _resolution_text(x, y):
    if x and y and x > 0 and y > 0: return f'{x:g} × {y:g} dpi'
    return 'Не указано'
def _fmt_size(n):
    for unit in ('Б','КиБ','МиБ','ГиБ'):
        if n < 1024 or unit=='ГиБ': return f'{n:.1f} {unit}' if unit!='Б' else f'{n} Б'
        n/=1024

def _png(f, size):
    if _read_exact(f,8) != b'\x89PNG\r\n\x1a\n': raise ParseError('Неверная сигнатура PNG')
    length=_u32(_read_exact(f,4),'>'); typ=_read_exact(f,4)
    if typ != b'IHDR' or length != 13: raise ParseError('Первый чанк PNG должен быть IHDR длиной 13 байт')
    d=_read_exact(f,13); w,h=_u32(d[:4],'>'),_u32(d[4:8],'>')
    bd,ct,comp,fil,inter=d[8:13]
    if not w or not h: raise ParseError('Нулевая ширина или высота')
    depths={0:[1,2,4,8,16],2:[8,16],3:[1,2,4,8],4:[8,16],6:[8,16]}
    if ct not in depths or bd not in depths[ct]: raise ParseError('Недопустимые глубина/тип цвета PNG')
    names={0:'без сжатия (тип цвета: grayscale)',2:'без сжатия (RGB)',3:'без сжатия (индексированный)',4:'без сжатия (grayscale + alpha)',6:'без сжатия (RGBA)'}
    # Проверяем структуру чанков до IEND, не загружая данные чанков целиком.
    f.seek(8); found=False
    while f.tell()+12 <= size:
        head=f.read(8)
        if len(head)<8: break
        ln=_u32(head[:4],'>'); typ=head[4:]
        if ln > size or f.tell()+ln+4 > size: raise ParseError('Размер чанка PNG выходит за границы файла')
        f.seek(ln+4,1)
        if typ==b'IEND':
            found=True
            if ln != 0: raise ParseError('Некорректная длина IEND')
            break
    if not found: raise ParseError('Отсутствует завершающий чанк IEND')
    f.seek(29)
    # DPI обычно хранится в необязательном pHYs; ищем его в чанках.
    f.seek(8); dpi='Не указано'
    while f.tell()+12 <= size:
        hd=f.read(8)
        if len(hd)<8: break
        ln=_u32(hd[:4],'>'); typ=hd[4:]
        if f.tell()+ln+4>size: break
        if typ==b'pHYs' and ln==9:
            dat=f.read(9); _read_exact(f,4)
            px,py,unit=_u32(dat[:4],'>'),_u32(dat[4:8],'>'),dat[8]
            if unit==1: dpi=_resolution_text(px*0.0254,py*0.0254)
        else: f.seek(ln+4,1)
        if typ==b'IEND': break
    return 'PNG',f'{w} × {h}',dpi,f'{bd} бит/пиксельный канал',names[ct],f'Цветовой тип: {ct}; фильтрация: метод {fil}; interlace: {inter}'

def _bmp(f, size):
    if _read_exact(f,2)!=b'BM': raise ParseError('Неверная сигнатура BMP')
    fh=_read_exact(f,12); declared=_u32(fh[:4]); off=_u32(fh[8:12]); dib_size=_u32(_read_exact(f,4))
    if dib_size<12 or dib_size>124: raise ParseError(f'Неподдерживаемый размер DIB-заголовка: {dib_size}')
    rest=_read_exact(f,dib_size-4)
    if dib_size==12:
        w,h=_u16(rest[:2]),_u16(rest[2:4]); planes=_u16(rest[4:6]); bpp=_u16(rest[6:8]); comp=0; xppm=yppm=0; colors=0
    else:
        w=_u32(rest[:4]); hraw=struct.unpack('<i',rest[4:8])[0]; h=abs(hraw); planes=_u16(rest[8:10]); bpp=_u16(rest[10:12]); comp=_u32(rest[12:16]); xppm=struct.unpack('<i',rest[20:24])[0]; yppm=struct.unpack('<i',rest[24:28])[0]; colors=_u32(rest[28:32])
    if not w or not h or planes!=1: raise ParseError('Некорректные размеры или число плоскостей BMP')
    if declared and declared>size: raise ParseError('Размер BMP в заголовке больше фактического файла')
    if off>size: raise ParseError('Смещение пиксельных данных выходит за границы файла')
    cm={0:'BI_RGB (без сжатия)',1:'BI_RLE8',2:'BI_RLE4',3:'BI_BITFIELDS',4:'BI_JPEG',5:'BI_PNG',6:'BI_ALPHABITFIELDS'}
    comp_name=cm.get(comp,f'Неизвестный код ({comp})')
    palette=colors or (max(0,2**bpp) if bpp<=8 else 0)
    dpi=_resolution_text(xppm*0.0254,yppm*0.0254) if xppm>0 and yppm>0 else 'Не указано'
    return 'BMP',f'{w} × {h}',dpi,f'{bpp} бит/пиксель',comp_name,f'Палитра: {palette} цветов (если используется); заголовок DIB: {dib_size} байт'

def _gif(f,size):
    sig=_read_exact(f,6)
    if sig not in (b'GIF87a',b'GIF89a'): raise ParseError('Неверная сигнатура GIF')
    d=_read_exact(f,7); w,h=_u16(d[:2]),_u16(d[2:4]); packed=d[4]
    if not w or not h: raise ParseError('Нулевой размер GIF')
    depth=(packed&7)+1; colors=2**depth if packed&0x80 else 0
    # В корректном GIF trailer — последний байт; читаем только конец файла.
    if size < 14: raise ParseError('Файл GIF слишком короткий')
    f.seek(-1, 2)
    if f.read(1) != b'\x3b': raise ParseError('Отсутствует завершающий маркер GIF (0x3B)')
    return 'GIF',f'{w} × {h}','Не указано',f'{depth} бит (таблица цветов: {colors or "нет глобальной"})','LZW',f'Версия: {sig.decode()}; глобальная палитра: {colors or 0} цветов'

def _pcx(f,size):
    h=_read_exact(f,128)
    if h[0]!=10 or h[2] not in (0,1) or h[1] not in (0,2,3,4,5): raise ParseError('Неверная сигнатура/версия PCX')
    xmin,ymin,xmax,ymax=struct.unpack('<4H',h[4:12]); w=xmax-xmin+1; he=ymax-ymin+1
    if w<=0 or he<=0: raise ParseError('Некорректные размеры PCX')
    bits=h[3]; planes=h[65]; bpl=_u16(h[66:68]); dpi=_resolution_text(_u16(h[12:14]),_u16(h[14:16]))
    if planes<1 or bits not in (1,2,4,8): raise ParseError('Некорректная глубина/число цветовых плоскостей PCX')
    depth=bits*planes
    comp='RLE (кодирование длин серий)' if h[2]==1 else 'без сжатия'
    return 'PCX',f'{w} × {he}',dpi,f'{depth} бит/пиксель',comp,f'Плоскостей: {planes}; байт на строку на плоскость: {bpl}'

def _tiff_value(f, typ, count, endian, value_field, filesize):
    sizes={1:1,2:1,3:2,4:4,5:8,6:1,7:1,8:2,9:4,10:8,11:4,12:8}
    if typ not in sizes or count>1000000: return None
    n=sizes[typ]*count
    if n<=4: raw=value_field[:n]
    else:
        off=_u32(value_field,endian)
        if off+n>filesize: raise ParseError('TIFF-тег ссылается за пределы файла')
        pos=f.tell(); f.seek(off); raw=f.read(n); f.seek(pos)
        if len(raw)!=n: raise ParseError('Обрезанные данные TIFF-тега')
    if typ in (3,8): fmt='H' if typ==3 else 'h'; step=2
    elif typ in (4,9,11): fmt='I' if typ==4 else ('i' if typ==9 else 'f'); step=4
    elif typ in (5,10):
        vals=[]
        for i in range(count):
            a,b=struct.unpack(endian+('II' if typ==5 else 'ii'),raw[i*8:i*8+8]); vals.append(a/b if b else 0)
        return vals
    elif typ==12: fmt='d'; step=8
    elif typ in (1,6,7): return list(raw)
    elif typ==2: return raw.rstrip(b'\0').decode('ascii','replace')
    else: return None
    return list(struct.unpack(endian+fmt*count,raw))

def _tiff(f,size):
    sig=_read_exact(f,8); endian='<' if sig[:2]==b'II' else '>' if sig[:2]==b'MM' else None
    if not endian or _u16(sig[2:4],endian)!=42: raise ParseError('Неверная сигнатура TIFF')
    off=_u32(sig[4:8],endian)
    if off+2>size: raise ParseError('Смещение IFD за пределами TIFF')
    f.seek(off); count=_u16(_read_exact(f,2),endian)
    if count>4096 or off+2+count*12+4>size: raise ParseError('Повреждённая таблица TIFF IFD')
    tags={}
    for _ in range(count):
        e=_read_exact(f,12); tag=_u16(e[:2],endian); typ=_u16(e[2:4],endian); n=_u32(e[4:8],endian)
        try: val=_tiff_value(f,typ,n,endian,e[8:12],size)
        except ParseError: raise
        if val is not None: tags[tag]=val
    def first(tag,default=None):
        v=tags.get(tag,default); return v[0] if isinstance(v,list) and v else v
    w,h=first(256),first(257)
    if not isinstance(w,(int,float)) or not isinstance(h,(int,float)) or w<=0 or h<=0: raise ParseError('В TIFF не найдены корректные теги ширины/высоты')
    bps=tags.get(258,[1]); depth=sum(bps) if isinstance(bps,list) else bps
    compression={1:'без сжатия',2:'CCITT 1D',3:'Group 3 Fax',4:'Group 4 Fax',5:'LZW',6:'JPEG (старый TIFF)',7:'JPEG',8:'Deflate',32773:'PackBits'}
    c=first(259,1); unit=first(296,2); xr=first(282); yr=first(283)
    try:
        if xr and yr:
            factor=1 if unit==2 else 2.54 if unit==3 else 1
            dpi=_resolution_text(float(xr)*factor,float(yr)*factor) if unit in (2,3) else 'Не указано (единица TIFF не задана)'
        else: dpi='Не указано'
    except Exception: dpi='Не указано'
    return 'TIFF',f'{int(w)} × {int(h)}',dpi,f'{depth} бит/пиксель',compression.get(c,f'код {c}'),f'Байтовый порядок: {"little-endian" if endian=="<" else "big-endian"}; samples/pixel: {first(277,"не указано")}'

def _jpeg(f,size):
    if _read_exact(f,2)!=b'\xff\xd8': raise ParseError('Неверная сигнатура JPEG')
    w=h=depth=components=None; dpi='Не указано'; sof={0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}
    while f.tell()<size:
        b=f.read(1)
        if not b: break
        if b!=b'\xff': continue
        while True:
            m=f.read(1)
            if not m: break
            if m!=b'\xff': break
        if not m: break
        marker=m[0]
        if marker in (0xD9,0xDA): break
        if marker in range(0xD0,0xD8) or marker==0x01: continue
        lb=f.read(2)
        if len(lb)<2: raise ParseError('Обрезан сегмент JPEG')
        ln=_u16(lb,'>')
        if ln<2 or f.tell()+ln-2>size: raise ParseError('Некорректная длина сегмента JPEG')
        data=f.read(ln-2)
        if marker in sof and len(data)>=6:
            depth=data[0]; h,w=struct.unpack('>HH',data[1:5]); components=data[5]
        elif marker==0xE0 and data[:5]==b'JFIF\0' and len(data)>=12:
            unit=data[7]; x,y=struct.unpack('>HH',data[8:12])
            if unit==1: dpi=_resolution_text(x,y)
            elif unit==2: dpi=_resolution_text(x*2.54,y*2.54)
        if w and h: # продолжаем искать JFIF DPI, но не читаем изображения целиком
            pass
    if not w or not h: raise ParseError('Не найден маркер кадра JPEG (SOF)')
    # Ищем EOI с конца файла, потоково.
    f.seek(max(0,size-65536)); tail=f.read()
    if b'\xff\xd9' not in tail: raise ParseError('Отсутствует завершающий маркер JPEG EOI (FF D9)')
    return 'JPEG',f'{w} × {h}',dpi,f'{depth} бит на компоненту ({components} компонент.)','обычно DCT; режим определяется SOF',f'Компонентов изображения: {components}'

PARSERS={'.png':_png,'.bmp':_bmp,'.gif':_gif,'.pcx':_pcx,'.tif':_tiff,'.tiff':_tiff,'.jpg':_jpeg,'.jpeg':_jpeg}

def read_image_info(path):
    name=os.path.basename(path); size=os.path.getsize(path)
    result=ImageInfo(name,path,file_size=_fmt_size(size))
    ext=os.path.splitext(name)[1].lower()
    if ext not in SUPPORTED:
        result.status='Пропущен: неподдерживаемое расширение'; return result
    try:
        with open(path,'rb') as f:
            # Определяем формат по сигнатуре, а не только по расширению.
            sig=f.read(8); f.seek(0)
            if sig.startswith(b'\x89PNG\r\n\x1a\n'): actual='.png'
            elif sig.startswith(b'BM'): actual='.bmp'
            elif sig[:6] in (b'GIF87a',b'GIF89a'): actual='.gif'
            elif sig[:2]==b'\xff\xd8': actual='.jpg'
            elif sig[:2] in (b'II',b'MM'): actual='.tif'
            elif sig[0:1]==b'\x0a': actual='.pcx'
            else: raise ParseError('Неизвестная сигнатура файла: содержимое не похоже на поддерживаемое изображение')
            parser=PARSERS[actual]
            fmt,dims,res,depth,compression,details=parser(f,size)
            result.format=fmt; result.dimensions=dims; result.resolution=res; result.color_depth=depth; result.compression=compression; result.details=details
            if actual != ext and not (actual=='.jpg' and ext=='.jpeg') and not (actual=='.tif' and ext=='.tiff'):
                result.status=f'Предупреждение: расширение {ext or "без расширения"}, формат по сигнатуре — {fmt}'
    except (OSError,ParseError,struct.error,ValueError,OverflowError) as e:
        result.status=f'Файл поврежден / не прочитан: {e}'
    except Exception as e:
        result.status=f'Ошибка чтения: {type(e).__name__}: {e}'
    return result

if __name__=='__main__':
    import sys
    for p in sys.argv[1:]: print(asdict(read_image_info(p)))
