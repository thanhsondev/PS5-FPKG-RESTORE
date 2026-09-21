#include "../src/pkg_reader.h"
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    Package p={0};p.file=fopen(argv[1],"rb");if(!p.file)return 2;
    PKG_SEEK(p.file,0,SEEK_END);
#ifdef _WIN32
    p.size=(uint64_t)_ftelli64(p.file);
#else
    p.size=(uint64_t)ftello(p.file);
#endif
    if(!pkg_parse(&p)){fclose(p.file);return 1;}
    if(!title_valid("PPSA12345")||title_valid("PPSA1234/")||title_valid("CUSA12345"))return 3;
    for(unsigned i=0;i<p.count;i++) {
        unsigned char *b=pkg_data(&p,&p.items[i]);if(!b)return 3;
        printf("%s %u\n",p.items[i].name,p.items[i].size);free(b);
    }
    fclose(p.file);return 0;
}
