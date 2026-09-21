/* PS5 Storage Restore 1.1 EN/VI. Existing installed FIH PKGs only.
 * NGÔ PHI PHƯƠNG - NGUYỄN THANH SƠN - PSVIETHOA.COM */
#include "pkg_reader.h"
#include <errno.h>
#include <unistd.h>
#include <dirent.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/uio.h>
#include <dlfcn.h>
#include <ps5/kernel.h>
#include <json-c/json.h>
#define STATE "/data/ps5_storage_restore"
extern int sceKernelSendNotificationRequest(int,void *,size_t,int);
extern int32_t sceSystemServiceParamGetInt(int32_t,int32_t *);
static FILE *logfile;
static int vietnamese;
static const char *tr(const char *vi,const char *en){return vietnamese?vi:en;}
static unsigned found,ok,skipped,created;
static int (*register_title)(const char *,const char *,void *);
static void notice(const char *s) {
    unsigned char b[3120]={0};snprintf((char *)b+45,sizeof(b)-45,
        "PS5 STORAGE RESTORE\n%s\n%s: NGÔ PHI PHƯƠNG - NGUYỄN THANH SƠN - PSVIETHOA.COM",
        s,tr("Bản quyền","Copyright"));
    sceKernelSendNotificationRequest(0,b,sizeof(b),0);
}
static int directory(const char *path) {
    struct stat st;
    if(!lstat(path,&st))return S_ISDIR(st.st_mode);
    return errno==ENOENT&&!mkdir(path,0777);
}
static int empty_dir(const char *path) {
    DIR *d=opendir(path);if(!d)return 0;struct dirent *e;int empty=1;
    while((e=readdir(d)))if(strcmp(e->d_name,".")&&strcmp(e->d_name,"..")){empty=0;break;}
    closedir(d);return empty;
}
static int same_file(const char *path,const unsigned char *b,size_t n) {
    struct stat st;if(lstat(path,&st)||!S_ISREG(st.st_mode)||(uint64_t)st.st_size!=n)return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    unsigned char buf[16384];size_t pos=0;int same=1;
    while(pos<n){size_t k=n-pos;if(k>sizeof(buf))k=sizeof(buf);
        if(fread(buf,1,k,f)!=k||memcmp(buf,b+pos,k)){same=0;break;}pos+=k;}
    fclose(f);return same;
}
/* Preserve existing artwork; param.json and ownership records must match. */
static int stage_file(const char *path,const unsigned char *b,size_t n,int write_it,int keep_existing) {
    struct stat st;
    if(!lstat(path,&st))return S_ISREG(st.st_mode)&&(keep_existing||same_file(path,b,n));
    if(errno!=ENOENT)return 0;
    if(!write_it)return 1;
    char temp[640];snprintf(temp,sizeof(temp),"%s.restore-%d.tmp",path,getpid());
    int fd=open(temp,O_WRONLY|O_CREAT|O_EXCL,0644);if(fd<0)return 0;
    size_t pos=0;int success=1;
    while(pos<n){ssize_t k=write(fd,b+pos,n-pos);if(k<0&&errno==EINTR)continue;
        if(k<=0){success=0;break;}pos+=(size_t)k;}
    if(success&&fsync(fd))success=0;
    if(close(fd))success=0;
    if(success&&!same_file(temp,b,n))success=0;
    if(success) {
        if(!lstat(path,&st))success=S_ISREG(st.st_mode)&&(keep_existing||same_file(path,b,n));
        else if(errno!=ENOENT||rename(temp,path))success=0;
        else {created++;fprintf(logfile,"CREATED %s bytes=%zu\n",path,n);}
    }
    unlink(temp);return success;
}
static int validate_param(Package *p,const char *title) {
    for(unsigned i=0;i<p->count;i++)if(!strcmp(p->items[i].name,"param.json")) {
        PkgItem *item=&p->items[i];if(item->size>1024*1024)return 0;
        unsigned char *b=pkg_data(p,item);if(!b)return 0;
        unsigned off=item->size>=3&&!memcmp(b,"\xef\xbb\xbf",3)?3:0;
        struct json_tokener *tok=json_tokener_new();if(!tok){free(b);return 0;}
        json_tokener_set_flags(tok,JSON_TOKENER_STRICT);
        struct json_object *obj=json_tokener_parse_ex(tok,(char *)b+off,(int)item->size-off);
        struct json_object *id=NULL;int good=json_tokener_get_error(tok)==json_tokener_success&&obj&&
            json_object_object_get_ex(obj,"titleId",&id)&&json_object_is_type(id,json_type_string)&&
            !strcmp(json_object_get_string(id),title);
        if(obj)json_object_put(obj);json_tokener_free(tok);free(b);return good;
    }
    return 0;
}
static int marker_matches(const char *marker,const char *source) {
    char b[320];FILE *f=fopen(marker,"rb");if(!f)return 0;
    size_t n=fread(b,1,sizeof(b)-1,f);fclose(f);b[n]=0;
    if(n&&b[n-1]=='\n')b[--n]=0;return !strcmp(b,source);
}
static void process_title(const char *root,const char *id,int internal) {
    char source[256],dest[256],pkgpath[320],meta[320],appmeta[256],marker[256];
    struct stat st;struct statfs fs;int new_dir=0,new_mount=0,success=0;
    snprintf(source,sizeof(source),"%s/%s",root,id);snprintf(dest,sizeof(dest),"/user/app/%s",id);
    snprintf(pkgpath,sizeof(pkgpath),"%s/app.pkg",source);
    snprintf(meta,sizeof(meta),"%s/sce_sys",source);snprintf(appmeta,sizeof(appmeta),"/user/appmeta/%s",id);
    snprintf(marker,sizeof(marker),STATE "/owned/%s",id);
    if(lstat(source,&st)||!S_ISDIR(st.st_mode))return;
    /* Internal scan ignores aliases already handled through the actual device. */
    if(internal&&!statfs(source,&fs)&&!strcmp(fs.f_fstypename,"nullfs"))return;
    if(lstat(pkgpath,&st)||!S_ISREG(st.st_mode))return;
    found++;fprintf(logfile,"FOUND %s source=%s bytes=%llu\n",id,source,(unsigned long long)st.st_size);fflush(logfile);
    Package p={0};p.size=(uint64_t)st.st_size;p.file=fopen(pkgpath,"rb");
    if(!p.file||!pkg_parse(&p)){fprintf(logfile,"SKIP invalid/unsupported PKG table %s\n",id);goto done;}
    if(!validate_param(&p,id)){fprintf(logfile,"SKIP invalid param.json/titleId %s\n",id);goto done;}
    int mounted=!internal&&!statfs(dest,&fs)&&!strcmp(fs.f_fstypename,"nullfs")&&
        !strcmp(fs.f_mntonname,dest)&&!strcmp(fs.f_mntfromname,source)&&(fs.f_flags&MNT_RDONLY);
    if(!internal&&!mounted) {
        if(!lstat(dest,&st)) {
            if(!S_ISDIR(st.st_mode)||!marker_matches(marker,source)||!empty_dir(dest)) {
                fprintf(logfile,"SKIP occupied/unowned destination %s\n",dest);goto done;
            }
        }else if(errno!=ENOENT){fprintf(logfile,"SKIP destination inaccessible %s\n",dest);goto done;}
    }
    if(!directory(meta)||!directory(appmeta)){fprintf(logfile,"SKIP metadata directory unavailable %s\n",id);goto done;}
    /* Check all existing resources before creating any file for this title. */
    for(int pass=0;pass<2;pass++)for(unsigned i=0;i<p.count;i++) {
        PkgItem *item=&p.items[i];unsigned char *b=pkg_data(&p,item);char a[512],c[512];
        snprintf(a,sizeof(a),"%s/%s",meta,item->name);snprintf(c,sizeof(c),"%s/%s",appmeta,item->name);
        int keep=strcmp(item->name,"param.json")!=0;
        int good=b&&stage_file(a,b,item->size,pass,keep)&&stage_file(c,b,item->size,pass,keep);free(b);
        if(!good){fprintf(logfile,"SKIP metadata conflict/write failed %s %s errno=%d\n",id,item->name,errno);goto done;}
    }
    if(!internal) {
        /* Record ownership before creating an alias; never replace another source. */
        char line[320];snprintf(line,sizeof(line),"%s\n",source);
        if(!stage_file(marker,(unsigned char *)line,strlen(line),1,0)) {fprintf(logfile,"SKIP marker conflict/write failure %s errno=%d\n",id,errno);goto done;}
        if(!mounted) {
            if(lstat(dest,&st)) {
                if(errno!=ENOENT||mkdir(dest,0777)){fprintf(logfile,"SKIP mkdir %s errno=%d\n",id,errno);goto done;}
                new_dir=1;
            }
            char *v[]={"fstype","nullfs","from",source,"fspath",dest};struct iovec iov[6];
            for(unsigned i=0;i<6;i++){iov[i].iov_base=v[i];iov[i].iov_len=strlen(v[i])+1;}
            if(nmount(iov,6,MNT_RDONLY)){fprintf(logfile,"MOUNT_FAILED %s errno=%d\n",id,errno);goto done;}
            new_mount=1;
        }
    }
    int rc=register_title(id,"/user/app/",NULL);
    fprintf(logfile,"REGISTER %s rc=0x%08x mode=%s\n",id,rc,internal?"internal-direct":"external-readonly");
    success=rc==0||(unsigned)rc==0x80990002u;
done:
    if(p.file)fclose(p.file);
    if(success)ok++;
    else {
        skipped++;
        if(new_mount&&unmount(dest,0)){fprintf(logfile,"ROLLBACK unmount failed %s errno=%d\n",dest,errno);new_dir=0;}
        if(new_dir)rmdir(dest);
    }
    fflush(logfile);
}
static void scan(const char *root,int internal) {
    struct stat st;if(lstat(root,&st)||!S_ISDIR(st.st_mode))return;
    DIR *d=opendir(root);if(!d)return;
    fprintf(logfile,"SCAN %s\n",root);struct dirent *e;
    while((e=readdir(d)))if(title_valid(e->d_name))process_title(root,e->d_name,internal);
    closedir(d);
}
int main(void) {
    int32_t system_language=-1;
    int lang_rc=sceSystemServiceParamGetInt(1,&system_language);
    vietnamese=lang_rc==0&&system_language==28;
    if(!directory(STATE)||!directory(STATE "/owned")){notice(tr("Không tạo được thư mục lưu trạng thái.","Cannot create state directory."));return 1;}
    int lock=open(STATE "/running.lock",O_RDWR|O_CREAT,0600);
    if(lock<0||flock(lock,LOCK_EX|LOCK_NB)){if(lock>=0)close(lock);notice(tr("Đang có phiên chạy khác hoặc không khóa được phiên.","Another instance is running or the session lock is unavailable."));return 1;}
    logfile=fopen(STATE "/restore.log","a");if(!logfile){close(lock);notice(tr("Không mở được file nhật ký.","Cannot open log file."));return 1;}
    fprintf(logfile,"START version=1.1-EN-VI pid=%d\nCopyright: NGÔ PHI PHƯƠNG - NGUYỄN THANH SƠN - PSVIETHOA.COM\nLANG system=%d rc=0x%08x selected=%s\n",getpid(),system_language,lang_rc,vietnamese?"vi":"en");fflush(logfile);
    notice(tr("Đang quét game trên bộ nhớ trong và SSD M.2...","Scanning games on internal storage and M.2 SSD..."));
    uint64_t prior=kernel_get_ucred_authid(-1);kernel_set_ucred_authid(-1,0x4800000000000006ULL);
    void *h=dlopen("/system/common/lib/libSceAppInstUtil.sprx",RTLD_LAZY);
    int (*init)(void)=h?dlsym(h,"sceAppInstUtilInitialize"):NULL;
    register_title=h?dlsym(h,"sceAppInstUtilAppInstallTitleDir"):NULL;
    int result=1;
    if(!init||!register_title) {fprintf(logfile,"ERROR AppInst API unavailable\n");notice(tr("Không nạp được AppInst. Xem file nhật ký.","Cannot load AppInst. Check the log."));goto finish;}
    fprintf(logfile,"INIT rc=0x%08x\n",init());
    if(!directory("/user/app")||!directory("/user/appmeta")){fprintf(logfile,"ERROR app directories unavailable\n");notice(tr("Không truy cập được thư mục game hệ thống.","Cannot access system application directories."));goto finish;}
    /* Direct internal installs win if a title also exists on another drive. */
    scan("/user/app",1);
    for(unsigned n=0;n<16;n++){char root[64];snprintf(root,sizeof(root),"/mnt/ext%u/user/app",n);scan(root,0);}
    char message[256];snprintf(message,sizeof(message),tr(
        "Đã đăng ký %u/%u game/ứng dụng. Bỏ qua: %u.\nMở Thư viện trò chơi để kiểm tra.",
        "Registered %u/%u games/apps. Skipped: %u.\nOpen Game Library to check."),ok,found,skipped);notice(message);
    result=skipped?2:0;
finish:
    kernel_set_ucred_authid(-1,prior);
    fprintf(logfile,"END registered=%u found=%u skipped=%u created=%u\n",ok,found,skipped,created);
    fclose(logfile);close(lock);return result;
}
