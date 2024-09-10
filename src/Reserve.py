import requests
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.utils import formataddr
import logging

TOMORROW = str(datetime.date.today() + datetime.timedelta(days=1))
TODAY = str(datetime.date.today())

INFO = {
    # 账号
    'account': '21111604029',
    # 密码
    'password': 'nsk3030',
    # 座位编号
    'sid': '',
    # 预约日期
    'atDate': TOMORROW,
    # 开始时间
    'st': TOMORROW + ' 16:00',
    # 结束时间
    'et': TOMORROW + ' 22:00',
    # 日志保存位置
    'fileloc': ''

}

EMAIL_INFO = {
    # 邮件接收者
    'to_user': '',
    # 邮件发送者
    'my_sender': '',
    # 邮箱密码(这里是设置授权码，并不是真正的密码)
    'my_pass': '',
    # 配置发件人昵称
    'my_nick': '',
    # 配置收件人昵称
    'to_nick': '',
    # 邮件内容
    'mail_msg': '''
                <p>尊敬的{0}：<p>
                <p>您明天的座位已经预约完成，请您及时登录自己的账户查看哦！<p>
                '''.format(INFO['account'])
}


class Reserve:
    def __init__(self, **kwargs):
        self.info = kwargs
        self.session = requests.Session()
        logging.basicConfig(filename=self.info['fileloc'], level=logging.DEBUG,
                            format=' %(asctime)self.session - %(levelname)self.session- %(message)self.session')

    def reserve(self):
        self.login()
        try:
            self.info['sid'] = self.convert(self.info['sid'])
            # 开始预约
            logging.info('begin to reserve...')
            header = {
                # 设定报文头
                'Host': 'libzwxt.ahnu.edu.cn',
                'Origin': 'http://libzwxt.ahnu.edu.cn',
                'Referer': 'http://libzwxt.ahnu.edu.cn/SeatWx/Seat.aspx?fid=3&sid=1438',
                'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
                'X-AjaxPro-Method': 'AddOrder',
            }
            reserveUrl = 'http://libzwxt.ahnu.edu.cn/SeatWx/ajaxpro/SeatManage.Seat,SeatManage.ashx'
            reserverData = {
                'atDate': self.info['atDate'],
                'sid': self.info['sid'],
                'st': self.info['st'],
                'et': self.info['et'],
            }

            # 尝试进行预约
            reserve = self.session.post(reserveUrl, data=json.dumps(reserverData), headers=header)
            if '成功' in reserve.text:
                logging.info(reserve.text)
                logging.info('reserve successfully! Your seat id is {0}'.format(self.info['sid']))
                email = Email(**EMAIL_INFO)
                email.send()

            while '预约成功' not in reserve.text:
                # 预约未成功，再次尝试
                reserve = self.session.post(reserveUrl, data=json.dumps(reserverData), headers=header)

                # 服务器时间不一致
                if '提前' in reserve.text:
                    logging.warning(reserve.text)
                    continue
                elif '冲突' or '重复' in reserve.text:
                    # 时间和其他人有冲突，顺延下一个座位
                    logging.warning(reserve.text)
                    logging.warning('Appointment failed, trying to reserve another seat...')
                    self.info['sid'] = str(int(self.info['sid']) + 1)
                    print(self.info['sid'])
                    continue
                elif '二次' in reserve.text:
                    logging.info(reserve.text)
                    break
                elif '成功' in reserve.text:
                    # 预约完成
                    logging.info(reserve.text)
                    logging.info('reserve successfully! Your seat id is {0}'.format(self.info['sid']))
                    email = Email(**EMAIL_INFO)
                    email.send()
                    break
                else:
                    logging.info(reserve.text)
                    logging.error('未知原因，未预约成功，请检查日志及数据设置！！！')
        except BaseException as e:
            logging.error(e)

    def login(self):
        logging.info('''
                    start  with self.info['account']:{0}, self.info['password']:{1}, seatid:{2}. From {3} to {4}.'''
                     .format(self.info['account'], self.info['password'], self.info['sid'], self.info['st'],
                             self.info['et']))

        # 开始登陆
        postUrl = 'http://libzwxt.ahnu.edu.cn/SeatWx/login.aspx'
        postData = {
            '__VIEWSTATE': '/wEPDwULLTE0MTcxNzMyMjZkZAl5GTLNAO7jkaD1B+BbDzJTZe4WiME3RzNDU4obNxXE',
            '__VIEWSTATEGENERATOR': 'F2D227C8',
            '__EVENTVALIDATION': '/wEWBQK1odvtBQLyj/OQAgKXtYSMCgKM54rGBgKj48j5D4sJr7QMZnQ4zS9tzQuQ1arifvSWo1qu0EsBRnWwz6pw',
            'tbUserName': self.info['account'],
            'tbPassWord': self.info['password'],
            'Button1': '登 录',
            'hfurl': ''
        }

        login = self.session.post(postUrl, data=postData)

        if '个人中心' in login.content.decode():
            logging.info('login successfully!')

    @staticmethod
    def convert(seat_code):
        sid = 0
        if seat_code[:3] == 'nzr':
            sid = int(seat_code[3:]) + 437
        elif seat_code[:3] == 'nsk' and seat_code[3] == '1':
            sid = int(seat_code[3:]) + 95
        elif seat_code[:3] == 'nsk' and seat_code[3] == '3':
            sid = int(seat_code[3:]) - 2477
        elif seat_code[:3] == 'nsk' and seat_code[3] == '2':
            sid = int(seat_code[3:]) - 1177
        elif seat_code[:3] == 'nbz':
            sid = int(seat_code[3:])
        return sid


class Email:
    def __init__(self, **kwargs):
        self.emailInfo = kwargs

    def setting(self):
        msg = MIMEText(self.emailInfo['mail_msg'], 'html', 'utf-8')
        msg['Form'] = formataddr([self.emailInfo['my_nick'], self.emailInfo['my_sender']])
        msg['To'] = formataddr([self.emailInfo['to_nick'], self.emailInfo['to_user']])
        msg['Subject'] = '图书馆座位预约'
        return msg

    def send(self):
        msg = self.setting()
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(self.emailInfo['my_sender'], self.emailInfo['my_pass'])
        server.sendmail(self.emailInfo['my_sender'], [self.emailInfo['to_user'], ],
                        msg.as_string())
        server.quit()
        logging.info('The email has been sent to {0}'.format(self.emailInfo['to_user']))


if __name__ == '__main__':
    reserve = Reserve(**INFO)
    reserve.reserve()
